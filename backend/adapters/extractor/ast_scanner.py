"""Extraccion estatica (ast) del grafo de tools/MCP/data-flows de un agente Python.

Todo lo que produce este modulo sale de hechos AST verificables (nombre, ubicacion,
llamadas dentro del cuerpo de la funcion) — no inventa nada. Donde ast no alcanza para
decidir un campo con certeza (p.ej. side_effects por defecto), se usa una regla
determinista y documentada, no una "opinion": es reproducible y testeable.

Cada archivo .py del repo se parsea UNA sola vez (`parse_repo`) y el ast.Module resultante
se reusa entre todos los scan_*, en vez de que cada uno re-lea y re-parsee el repo entero.

Limite MVP conocido en la resolucion de scope de `_shadowed_at`/`_referenced_elsewhere`
(usada por `scan_secrets` para `in_context`): sigue la regla general de Python (cualquier
binding hace local a un nombre en su funcion, `global`/`nonlocal` lo saca, se sube por la
cadena de closures) pero NO modela el scope propio de comprehensions (list/set/dict/gen) ni
bindings de `with ... as` / reasignaciones dentro de `if`/`try` a nivel de modulo. Para el
tamano de agente que este extractor analiza en el MVP (repos chicos de hackathon, no
codebases enterprise) esto es una degradacion aceptada, no un objetivo de dataflow analyzer
completo.
"""

from __future__ import annotations

import ast
import hashlib
import logging
from pathlib import Path

from contracts import (
    AgentInfo,
    AgentLoop,
    DataFlow,
    FlowEndpoint,
    McpServer,
    McpTool,
    Rag,
    Secret,
    Tool,
    ToolParameter,
)

logger = logging.getLogger(__name__)

ParsedFile = tuple[Path, ast.Module]

_SHELL_CALLS = {
    "subprocess.run", "subprocess.Popen", "subprocess.call",
    "subprocess.check_output", "os.system", "os.popen",
}
_SQL_CALLS = {"sqlite3.connect", "psycopg2.connect"}
_HTTP_CALLS = {
    "httpx.get", "httpx.post", "httpx.put", "httpx.request",
    "requests.get", "requests.post", "requests.put", "requests.request",
    "urllib.request.urlopen",
}
_FS_CALLS = {"open", "pathlib.Path"}
_VECTOR_STORE_NAMES = {
    "Chroma", "Pinecone", "FAISS", "Weaviate", "Qdrant", "Milvus", "PGVector",
}

_SANITIZER_HINTS = ("saniti", "escape", "quote", "validate", "allowlist")

_KIND_DEFAULT_SIDE_EFFECTS = {
    "shell": "destructive",
    "sql": "read",
    "http": "write",
    "filesystem": "write",
    "code_exec": "none",
}
_READ_HINTS = ("read", "search", "get", "query", "fetch", "list")
_DESTRUCTIVE_HINTS = ("delete", "drop", "remove", "destroy")

_SINK_KIND = {
    "shell": "shell_exec",
    "sql": "sql_exec",
    "http": "http_request",
    "filesystem": "file_io",
    "code_exec": "exec",
}


def _rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def _iter_py_files(root: Path):
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(), filename=str(path))
    except SyntaxError:
        return None


def parse_repo(root: Path) -> list[ParsedFile]:
    """Parsea cada .py del repo una sola vez; los archivos con SyntaxError se omiten."""
    parsed: list[ParsedFile] = []
    for path in _iter_py_files(root):
        tree = _parse(path)
        if tree is not None:
            parsed.append((path, tree))
    return parsed


def _call_dotted_name(node: ast.AST) -> str | None:
    """Reconstruye 'subprocess.run' desde un ast.Call.func, o None si no aplica."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    parts: list[str] = []
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if isinstance(func, ast.Name):
        parts.append(func.id)
    else:
        return None
    return ".".join(reversed(parts))


def _has_kwarg_true(node: ast.Call, name: str) -> bool:
    for kw in node.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant) and kw.value.value is True:
            return True
    return False


def _classify_tool(func: ast.FunctionDef) -> tuple[str, bool]:
    """-> (kind, full_shell_detected). `full_shell` significa "corre via un shell completo,
    cualquier binario del PATH es alcanzable" -- cierto para subprocess.*(shell=True) pero
    TAMBIEN para os.system/os.popen, que siempre pasan por /bin/sh -c sin necesitar ese kwarg.
    """
    for node in ast.walk(func):
        dotted = _call_dotted_name(node)
        if dotted is None:
            continue
        if dotted in _SHELL_CALLS:
            always_full_shell = dotted in {"os.system", "os.popen"}
            subprocess_shell_true = dotted.startswith("subprocess.") and _has_kwarg_true(
                node, "shell"
            )
            return "shell", always_full_shell or subprocess_shell_true
        if dotted in _SQL_CALLS or dotted.endswith(".execute"):
            return "sql", False
        if dotted in _HTTP_CALLS:
            return "http", False
        if dotted in _FS_CALLS:
            return "filesystem", False
    return "code_exec", False


def _default_side_effects(kind: str, name: str, doc: str) -> str:
    haystack = f"{name} {doc}".lower()
    if any(h in haystack for h in _DESTRUCTIVE_HINTS):
        return "destructive"
    if kind != "shell" and any(h in haystack for h in _READ_HINTS):
        return "read"
    return _KIND_DEFAULT_SIDE_EFFECTS[kind]


def _is_tool_decorated(func: ast.FunctionDef) -> bool:
    for dec in func.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Name) and target.id == "tool":
            return True
        if isinstance(target, ast.Attribute) and target.attr == "tool":
            return True
    return False


def _annotation_str(arg: ast.arg) -> str:
    if arg.annotation is None:
        return "string"
    try:
        return ast.unparse(arg.annotation)
    except (TypeError, ValueError, RecursionError):
        return "string"


def scan_tools(root: Path, parsed: list[ParsedFile]) -> list[Tool]:
    tools: list[Tool] = []
    for path, tree in parsed:
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not _is_tool_decorated(node):
                continue
            kind, shell_true = _classify_tool(node)
            doc = ast.get_docstring(node) or ""
            params = [
                ToolParameter(name=arg.arg, type=_annotation_str(arg), source_trust="untrusted")
                for arg in node.args.args
                if arg.arg != "self"
            ]
            tools.append(
                Tool(
                    id=f"tool.{node.name}",
                    name=node.name,
                    kind=kind,
                    defined_at=f"{_rel(root, path)}:{node.lineno}",
                    side_effects=_default_side_effects(kind, node.name, doc),
                    requires_approval=False,
                    parameters=params,
                    reachable_binaries=["sh"] if shell_true else [],
                )
            )
    return tools


def scan_mcp_servers(root: Path, parsed: list[ParsedFile]) -> list[McpServer]:
    servers: list[McpServer] = []
    for _path, tree in parsed:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(t, ast.Name) and t.id == "MCP_SERVERS" for t in node.targets):
                continue
            try:
                raw = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                continue
            for entry in raw:
                mcp_tools = [
                    McpTool(
                        name=t["name"],
                        description=t.get("description", ""),
                        description_hash="sha256:"
                        + hashlib.sha256(t.get("description", "").encode()).hexdigest()[:12],
                        schema_hash="sha256:"
                        + hashlib.sha256(repr(sorted(t.items())).encode()).hexdigest()[:12],
                        side_effects=t.get("side_effects", "read"),
                    )
                    for t in entry.get("tools", [])
                ]
                servers.append(
                    McpServer(
                        id=entry["id"],
                        name=entry["name"],
                        url=entry["url"],
                        transport=entry["transport"],
                        trust_level=entry["trust_level"],
                        tools=mcp_tools,
                    )
                )
    return servers


def _resolve_tool_call_target(call: ast.Call, tool_names: set[str]) -> str | None:
    func = call.func
    if (
        isinstance(func, ast.Attribute)
        and func.attr == "invoke"
        and isinstance(func.value, ast.Name)
        and func.value.id in tool_names
    ):
        return func.value.id
    if isinstance(func, ast.Name) and func.id in tool_names:
        return func.id
    return None


def _call_leaf_args(call: ast.Call) -> list[ast.AST]:
    leafs: list[ast.AST] = list(call.args) + [kw.value for kw in call.keywords]
    expanded: list[ast.AST] = []
    for node in leafs:
        if isinstance(node, ast.Dict):
            expanded.extend(node.values)
        else:
            expanded.append(node)
    return expanded


def _trace_taint(node: ast.AST, param_names: set[str]) -> tuple[bool, bool]:
    """-> (tainted_por_un_param, sanitized). Sigue dos formas de wrapping de una capa:

    - una llamada a funcion que recibe el param como argumento, p.ej. `shlex.quote(x)`
      (sanitiza si el nombre de la funcion matchea _SANITIZER_HINTS)
    - un metodo llamado sobre el param, p.ej. `x.strip()` (sigue tainted; NO sanitiza
      salvo que el nombre del metodo matchee _SANITIZER_HINTS)
    """
    if isinstance(node, ast.Name) and node.id in param_names:
        return True, False
    if isinstance(node, ast.Call):
        dotted = _call_dotted_name(node) or ""
        wrapped_args = [a for a in node.args if isinstance(a, ast.Name) and a.id in param_names]
        if wrapped_args:
            sanitized = any(h in dotted.lower() for h in _SANITIZER_HINTS)
            return True, sanitized
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id in param_names
        ):
            sanitized = any(h in func.attr.lower() for h in _SANITIZER_HINTS)
            return True, sanitized
    return False, False


def scan_data_flows(root: Path, parsed: list[ParsedFile], tools: list[Tool]) -> list[DataFlow]:
    tool_by_name = {t.name: t for t in tools}
    flows: list[DataFlow] = []
    flow_n = 0
    for path, tree in parsed:
        for func in ast.walk(tree):
            if not isinstance(func, ast.FunctionDef):
                continue
            param_names = {a.arg for a in func.args.args}
            if not param_names:
                continue
            for call in ast.walk(func):
                if not isinstance(call, ast.Call):
                    continue
                target_name = _resolve_tool_call_target(call, set(tool_by_name))
                if target_name is None:
                    continue
                sink_tool = tool_by_name[target_name]
                for arg_node in _call_leaf_args(call):
                    tainted, sanitized = _trace_taint(arg_node, param_names)
                    if not tainted:
                        continue
                    flow_n += 1
                    flows.append(
                        DataFlow(
                            id=f"flow.{flow_n}",
                            source=FlowEndpoint(
                                kind="user_input", at=f"{_rel(root, path)}:{func.lineno}"
                            ),
                            sink=FlowEndpoint(
                                kind=_SINK_KIND[sink_tool.kind], at=sink_tool.defined_at
                            ),
                            path=[f"{_rel(root, path)}:{func.lineno}", sink_tool.defined_at],
                            sanitized=sanitized,
                        )
                    )
    return flows


def _os_environ_subscript_key(node: ast.AST) -> str | None:
    """-> el nombre de la env var si `node` es `os.environ["X"]`, si no None."""
    if not isinstance(node, ast.Subscript):
        return None
    value = node.value
    is_os_environ = (
        isinstance(value, ast.Attribute)
        and value.attr == "environ"
        and isinstance(value.value, ast.Name)
        and value.value.id == "os"
    )
    if not is_os_environ:
        return None
    key = node.slice
    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        return key.value
    return None


def _iter_own_scope(node: ast.AST):
    """Yields `node` y sus descendientes, sin bajar a funciones/lambdas/clases anidadas --
    esas tienen su propio scope y sus bindings no son locales al scope de `node`."""
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        yield from _iter_own_scope(child)


def _assign_target_names(node: ast.AST) -> set[str]:
    targets: list[ast.AST] = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr, ast.For, ast.AsyncFor)):
        targets = [node.target]
    if not targets:
        return set()
    names: set[str] = set()
    for t in targets:
        names |= {n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
    return names


def _locals_of(func: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> set[str]:
    """Todo nombre que Python trata como local a `func`: cualquier parametro (incluyendo
    posicional-only) MAS cualquier target de asignacion en su cuerpo propio (Assign,
    AnnAssign, AugAssign, for-target, except-as, walrus) -- esa es la regla real de Python
    ("cualquier binding de ese nombre en el scope lo hace local"), no una lista de casos.
    `global`/`nonlocal` para ese nombre lo saca de la lista.
    """
    bound: set[str] = set()
    args = func.args
    for a in (*args.args, *args.posonlyargs, *args.kwonlyargs):
        bound.add(a.arg)
    if args.vararg:
        bound.add(args.vararg.arg)
    if args.kwarg:
        bound.add(args.kwarg.arg)

    nonlocal_names: set[str] = set()
    body = func.body if isinstance(func.body, list) else [func.body]
    for stmt in body:
        for node in _iter_own_scope(stmt):
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                nonlocal_names.update(node.names)
                continue
            if isinstance(node, ast.ExceptHandler) and node.name:
                bound.add(node.name)
            bound |= _assign_target_names(node)
    return bound - nonlocal_names


def _enclosing_scopes(tree: ast.Module, lineno: int) -> list[ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda]:
    """Cadena de funciones/lambdas que contienen `lineno`, de la MAS INTERNA a la MAS
    EXTERNA -- para resolver el nombre como Python (LEGB): primero el scope mas cercano,
    y si no liga ahi, subir un nivel, hasta llegar al modulo."""
    containing = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
        and node.lineno <= lineno <= getattr(node, "end_lineno", node.lineno)
    ]
    return sorted(containing, key=lambda n: n.lineno, reverse=True)


def _shadowed_at(tree: ast.Module, name: str, lineno: int) -> bool:
    """True si `name` es local a algun scope de la cadena de closures que contiene
    `lineno` (del mas cercano hacia afuera) -- esa referencia no llega a apuntar a la
    variable de modulo. No modela el scope propio de comprehensions (list/set/dict/gen)
    ni bindings de `with ... as` -- limite MVP conocido, ver docstring de modulo."""
    return any(name in _locals_of(scope) for scope in _enclosing_scopes(tree, lineno))


def _module_level_rebind_lines(tree: ast.Module, name: str, after_lineno: int) -> list[int]:
    """Lineas, a nivel de modulo (sin bajar a funciones), donde `name` se re-liga despues
    de `after_lineno` -- Assign/AnnAssign/AugAssign, no solo Assign simple."""
    lines = [
        node.lineno
        for node in tree.body
        if node.lineno > after_lineno and name in _assign_target_names(node)
    ]
    return sorted(lines)


def _referenced_elsewhere(tree: ast.Module, name: str, declared_lineno: int) -> bool:
    """True si `name` se lee (ast.Load) en otra linea del mismo archivo -- evidencia real
    de que el secreto se usa (p.ej. interpolado en un prompt/contexto), no solo declarado.

    Descarta dos falsos positivos de un match ciego por string: (1) el nombre esta shadowed
    (es local, por cualquier binding, no solo un parametro) en la funcion que contiene la
    referencia, y (2) la variable de modulo fue re-ligada (por cualquier forma de
    asignacion) antes de esa referencia -- en ese punto el nombre ya no apunta al valor
    original leido del entorno.
    """
    valid_until = next(iter(_module_level_rebind_lines(tree, name, declared_lineno)), None)

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Load)):
            continue
        if node.lineno == declared_lineno:
            continue
        if valid_until is not None and node.lineno >= valid_until:
            continue
        if _shadowed_at(tree, name, node.lineno):
            continue
        return True
    return False


def scan_secrets(root: Path, parsed: list[ParsedFile]) -> list[Secret]:
    secrets: list[Secret] = []
    for path, tree in parsed:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            dotted = _call_dotted_name(node.value) or ""
            is_env_read = (
                dotted in {"os.getenv", "os.environ.get"}
                or _os_environ_subscript_key(node.value) is not None
            )
            if not is_env_read:
                continue
            name_lower = target.id.lower()
            kind = "api_key" if "key" in name_lower else "token"
            # in_context: evidencia real de uso posterior, no un default fijo -- una var
            # leida del entorno y nunca mas referenciada no llega al contexto del modelo.
            in_context = _referenced_elsewhere(tree, target.id, node.lineno)
            secrets.append(
                Secret(
                    id=f"secret.{name_lower}",
                    at=f"{_rel(root, path)}:{node.lineno}",
                    kind=kind,
                    in_context=in_context,
                )
            )
    return secrets


def scan_rag(root: Path, parsed: list[ParsedFile]) -> Rag | None:
    """Heuristica: detecta instanciacion de un vector store conocido (p.ej. `Chroma(...)`,
    `vectorstores.Pinecone.from_documents(...)`). `ingestion_trusted` es conservador
    (False) por defecto -- ast no puede probar que la fuente de ingestion es confiable.
    """
    for path, tree in parsed:
        for node in ast.walk(tree):
            dotted = _call_dotted_name(node)
            if dotted is None:
                continue
            parts = dotted.split(".")
            match = next((p for p in parts if p in _VECTOR_STORE_NAMES), None)
            if match is None:
                continue
            return Rag(
                present=True,
                vector_store=match.lower(),
                ingestion_trusted=False,
                retrieval_at=f"{_rel(root, path)}:{node.lineno}",
            )
    return None


def scan_agent_loop(parsed: list[ParsedFile]) -> AgentLoop:
    max_iterations: int | None = None
    budget_enforced = False
    for _path, tree in parsed:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if target.id == "MAX_ITERATIONS":
                try:
                    max_iterations = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    logger.debug("MAX_ITERATIONS no es un literal evaluable; se usa el default")
            elif target.id == "BUDGET_ENFORCED":
                try:
                    budget_enforced = bool(ast.literal_eval(node.value))
                except (ValueError, SyntaxError):
                    logger.debug("BUDGET_ENFORCED no es un literal evaluable; se usa el default")
    return AgentLoop(max_iterations=max_iterations, budget_enforced=budget_enforced)


def scan_agent_info(root: Path, entrypoint: Path, parsed: list[ParsedFile]) -> AgentInfo:
    name = "agent"
    tree = next((t for p, t in parsed if p == entrypoint), None)
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id == "AGENT_NAME":
                    try:
                        name = ast.literal_eval(node.value)
                    except (ValueError, SyntaxError):
                        logger.debug("AGENT_NAME no es un literal evaluable; se usa el default")
    return AgentInfo(name=name, runtime="python", entrypoint=_rel(root, entrypoint))


def tools_containing_line(
    root: Path, parsed: list[ParsedFile], hit_path: Path, hit_line: int, tools: list[Tool]
) -> list[str]:
    """-> ids de tools cuyo cuerpo de funcion (por end_lineno) contiene `hit_line` en
    `hit_path`. Usa hechos AST reales (rango de la funcion), no una heuristica de cercania.
    """
    tree = next((t for p, t in parsed if p == hit_path), None)
    if tree is None:
        return []
    tools_by_defined_at = {t.defined_at: t.id for t in tools}
    matches: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        end = getattr(node, "end_lineno", node.lineno)
        if node.lineno <= hit_line <= end:
            key = f"{_rel(root, hit_path)}:{node.lineno}"
            if key in tools_by_defined_at:
                matches.append(tools_by_defined_at[key])
    return matches


def find_entrypoint(root: Path, parsed: list[ParsedFile]) -> Path:
    candidate = root / "src" / "agent.py"
    if candidate.exists():
        return candidate
    for path, tree in parsed:
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "TOOLS" for t in node.targets
            ):
                return path
    raise ValueError(f"no se encontro un entrypoint de agente (src/agent.py o TOOLS=...) bajo {root}")
