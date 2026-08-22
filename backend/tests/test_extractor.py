"""Tests del Extractor real (D1). Cubren los 4 criterios de aceptacion de
specs/03-components.md #C1 mas los guardrails de robustez (semgrep ausente, LLM sin
key, LLM anti-invencion).

Ejecuta:  uv run pytest tests/test_extractor.py
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from adapters.extractor import PyAstExtractor, ast_scanner, llm_enrich, semgrep_scan
from contracts import AgentArchitecture, Tool

TARGET_AGENT = Path(__file__).resolve().parents[2] / "target-agent"


def test_extract_meets_c1_acceptance_criteria():
    arch = PyAstExtractor().extract(str(TARGET_AGENT))

    # valida contra el Pydantic AgentArchitecture sin errores
    AgentArchitecture.model_validate(arch.model_dump())

    # >=1 tool shell y >=1 mcp_server con trust_level
    shell_tools = [t for t in arch.tools if t.kind == "shell"]
    assert shell_tools, "se esperaba al menos una tool 'shell'"
    assert arch.mcp_servers, "se esperaba al menos un mcp_server"
    assert all(s.trust_level for s in arch.mcp_servers)

    # data_flow user_input -> shell_exec sale con sanitized: false
    unsanitized_shell_flows = [
        f
        for f in arch.data_flows
        if f.source.kind == "user_input" and f.sink.kind == "shell_exec" and not f.sanitized
    ]
    assert unsanitized_shell_flows, "se esperaba un flujo user_input->shell_exec sin sanitizar"


def test_t1_adding_a_tool_changes_architecture(tmp_path):
    """Copia real de target-agent, le agrega query_database de verdad, y re-extrae."""
    v1_dir = tmp_path / "v1"
    v2_dir = tmp_path / "v2"
    shutil.copytree(TARGET_AGENT, v1_dir)
    shutil.copytree(TARGET_AGENT, v2_dir)

    (v2_dir / "src" / "tools" / "database.py").write_text(
        '"""query_database — agregada en vivo para probar T1."""\n\n'
        "from langchain_core.tools import tool\n\n\n"
        "@tool\n"
        "def query_database(query: str) -> str:\n"
        '    """Run a read query against the support ticket database."""\n'
        "    import sqlite3\n\n"
        '    conn = sqlite3.connect("tickets.db")\n'
        "    return str(conn.execute(query).fetchall())\n"
    )
    agent_py = v2_dir / "src" / "agent.py"
    agent_py.write_text(
        agent_py.read_text()
        .replace(
            "from .tools.shell import run_shell",
            "from .tools.database import query_database\nfrom .tools.shell import run_shell",
        )
        .replace(
            "TOOLS = [run_shell, send_email]",
            "TOOLS = [run_shell, send_email, query_database]",
        )
    )

    arch_v1 = PyAstExtractor().extract(str(v1_dir))
    arch_v2 = PyAstExtractor().extract(str(v2_dir))

    ids_v1 = {t.id for t in arch_v1.tools}
    ids_v2 = {t.id for t in arch_v2.tools}
    assert ids_v2 - ids_v1 == {"tool.query_database"}, (
        "architecture.json debe cambiar al agregar una tool (prueba T1)"
    )
    added = next(t for t in arch_v2.tools if t.id == "tool.query_database")
    assert added.kind == "sql"


def test_semgrep_missing_does_not_crash(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    hits = semgrep_scan.run_semgrep(TARGET_AGENT)
    assert hits is None  # degradacion explicita, no excepcion

    # la extraccion completa debe seguir funcionando sin semgrep
    arch = PyAstExtractor().extract(str(TARGET_AGENT))
    assert arch.tools


def test_llm_enrich_is_noop_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    arch = PyAstExtractor().extract(str(TARGET_AGENT))
    enriched = llm_enrich.enrich(arch)
    assert enriched == arch


def test_llm_enrich_discards_invented_entities(monkeypatch):
    """Guardrail anti-alucinacion: un id que el LLM inventa nunca llega al resultado."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    arch = PyAstExtractor().extract(str(TARGET_AGENT))

    fake_patch = llm_enrich._EnrichmentPatch(
        tools=[llm_enrich._ToolPatch(id="tool.invented_by_llm", side_effects="destructive")],
        mcp_servers=[llm_enrich._McpServerPatch(id="mcp.invented", trust_level="first_party")],
    )
    monkeypatch.setattr(llm_enrich, "_ask_llm", lambda _arch: fake_patch)

    result = llm_enrich.enrich(arch)
    assert {t.id for t in result.tools} == {t.id for t in arch.tools}
    assert {s.id for s in result.mcp_servers} == {s.id for s in arch.mcp_servers}


def test_scan_rag_detects_vector_store(tmp_path):
    (tmp_path / "rag.py").write_text(
        "from langchain_chroma import Chroma\n\n"
        "def build_store(docs, embeddings):\n"
        "    return Chroma.from_documents(docs, embeddings)\n"
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    rag = ast_scanner.scan_rag(tmp_path, parsed)
    assert rag is not None
    assert rag.present is True
    assert rag.vector_store == "chroma"
    assert rag.ingestion_trusted is False  # default conservador


def test_scan_rag_absent_by_default(tmp_path):
    (tmp_path / "plain.py").write_text("def f(x):\n    return x\n")
    parsed = ast_scanner.parse_repo(tmp_path)
    assert ast_scanner.scan_rag(tmp_path, parsed) is None


def test_scan_secrets_detects_environ_subscript(tmp_path):
    """os.environ["X"] ademas de os.getenv/os.environ.get (patron muy comun en repos reales)."""
    (tmp_path / "config.py").write_text(
        'import os\n\nSTRIPE_API_KEY = os.environ["STRIPE_API_KEY"]\n'
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    secrets = ast_scanner.scan_secrets(tmp_path, parsed)
    assert any(s.id == "secret.stripe_api_key" and s.kind == "api_key" for s in secrets)


def test_data_flow_detects_method_chain_taint(tmp_path):
    """message.strip() sigue siendo un flujo tainted -- no es un sanitizador."""
    (tmp_path / "handler.py").write_text(
        "def handle(message):\n"
        '    return run_shell.invoke({"command": message.strip()})\n'
    )
    fake_tool = Tool(
        id="tool.run_shell", name="run_shell", kind="shell",
        defined_at="tools/shell.py:1", side_effects="destructive",
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    flows = ast_scanner.scan_data_flows(tmp_path, parsed, [fake_tool])
    assert flows and flows[0].sanitized is False


def test_data_flow_sanitizer_call_marks_sanitized(tmp_path):
    """Guardia de regresion: shlex.quote(x) debe seguir marcando sanitized=True."""
    (tmp_path / "handler.py").write_text(
        "import shlex\n\n\n"
        "def handle(message):\n"
        '    return run_shell.invoke({"command": shlex.quote(message)})\n'
    )
    fake_tool = Tool(
        id="tool.run_shell", name="run_shell", kind="shell",
        defined_at="tools/shell.py:1", side_effects="destructive",
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    flows = ast_scanner.scan_data_flows(tmp_path, parsed, [fake_tool])
    assert flows and flows[0].sanitized is True


def test_scan_secrets_in_context_reflects_real_usage(tmp_path):
    """in_context ya no es un True fijo: una var leida y nunca mas referenciada no cuenta."""
    (tmp_path / "config.py").write_text(
        "import os\n\n"
        'UNUSED_KEY = os.getenv("UNUSED_KEY", "")\n'
        'USED_KEY = os.getenv("USED_KEY", "")\n\n'
        'PROMPT = f"context: {USED_KEY}"\n'
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    secrets = {s.id: s for s in ast_scanner.scan_secrets(tmp_path, parsed)}
    assert secrets["secret.unused_key"].in_context is False
    assert secrets["secret.used_key"].in_context is True


def test_semgrep_flags_uncovered_shell_sink(tmp_path, caplog):
    """Cuando ast no logra vincular un sink shell a ningun data_flow (p.ej. taint via
    f-string), pero Semgrep SI detecta subprocess.run(shell=True), se emite un warning
    puntual en vez de descartar en silencio el hallazgo de semgrep."""
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep no instalado en este entorno")

    src = tmp_path / "src"
    (src / "tools").mkdir(parents=True)
    (src / "tools" / "shell.py").write_text(
        "import subprocess\n"
        "from langchain_core.tools import tool\n\n\n"
        "@tool\n"
        "def run_shell(command: str) -> str:\n"
        '    """Run a shell command."""\n'
        "    result = subprocess.run(\n"
        "        command, shell=True, capture_output=True, text=True, check=False\n"
        "    )\n"
        "    return result.stdout\n"
    )
    (src / "agent.py").write_text(
        "from .tools.shell import run_shell\n\n"
        "TOOLS = [run_shell]\n\n\n"
        "def handle(message):\n"
        # f-string: _trace_taint no lo reconoce -> ast no genera data_flow para este sink
        '    return run_shell.invoke({"command": f"echo {message}"})\n'
    )

    caplog.set_level(logging.WARNING)
    PyAstExtractor().extract(str(tmp_path))

    assert any(
        "tool.run_shell" in r.message and "revisar manualmente" in r.message
        for r in caplog.records
    )


def test_scan_secrets_in_context_ignores_param_shadowing(tmp_path):
    """Un parametro homonimo en otra funcion no debe 'activar' in_context del secreto real."""
    (tmp_path / "config.py").write_text(
        "import os\n\n"
        'API_KEY = os.getenv("API_KEY", "")\n\n\n'
        "def unrelated(API_KEY):\n"
        "    return API_KEY.upper()\n"
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    secrets = {s.id: s for s in ast_scanner.scan_secrets(tmp_path, parsed)}
    assert secrets["secret.api_key"].in_context is False


def test_scan_secrets_in_context_ignores_stale_reference_after_reassignment(tmp_path):
    """Si la variable se reasigna, un uso posterior ya no evidencia que el secreto original
    llegue al contexto -- apunta al valor nuevo, no al leido del entorno."""
    (tmp_path / "config.py").write_text(
        "import os\n\n"
        'API_KEY = os.getenv("API_KEY", "")\n'
        'API_KEY = "***redacted***"\n'
        "print(API_KEY)\n"
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    secrets = {s.id: s for s in ast_scanner.scan_secrets(tmp_path, parsed)}
    assert secrets["secret.api_key"].in_context is False


def test_os_system_tool_gets_reachable_binaries(tmp_path):
    """os.system/os.popen siempre corren via un shell completo, sin necesitar shell=True
    (ese kwarg ni existe en su firma) -- deben marcar reachable_binaries igual que
    subprocess.run(shell=True)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "agent.py").write_text(
        "from langchain_core.tools import tool\n"
        "import os\n\n\n"
        "@tool\n"
        "def run_shell(command: str) -> str:\n"
        '    """Run a shell command."""\n'
        "    return str(os.system(command))\n\n\n"
        "TOOLS = [run_shell]\n"
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    tools = ast_scanner.scan_tools(tmp_path, parsed)
    run_shell = next(t for t in tools if t.name == "run_shell")
    assert run_shell.kind == "shell"
    assert run_shell.reachable_binaries == ["sh"]


def test_scan_secrets_in_context_ignores_for_loop_shadowing(tmp_path):
    """Shadowing no es solo por parametro: un target de `for` con el mismo nombre tambien
    hace que Python trate ese nombre como local a la funcion, no la variable de modulo."""
    (tmp_path / "config.py").write_text(
        "import os\n\n"
        'API_KEY = os.getenv("API_KEY", "")\n\n\n'
        "def rotate_keys(candidates):\n"
        "    for API_KEY in candidates:\n"
        "        print(API_KEY)\n"
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    secrets = {s.id: s for s in ast_scanner.scan_secrets(tmp_path, parsed)}
    assert secrets["secret.api_key"].in_context is False


def test_scan_secrets_in_context_ignores_stale_reference_after_annassign(tmp_path):
    """La reasignacion tambien puede venir de un AnnAssign (con anotacion de tipo), no
    solo de un Assign simple -- debe invalidar la evidencia igual que el caso sin anotar."""
    (tmp_path / "config.py").write_text(
        "import os\n\n"
        'API_KEY = os.getenv("API_KEY", "")\n'
        'API_KEY: str = "***redacted***"\n'
        "print(API_KEY)\n"
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    secrets = {s.id: s for s in ast_scanner.scan_secrets(tmp_path, parsed)}
    assert secrets["secret.api_key"].in_context is False


def test_scan_secrets_in_context_ignores_positional_only_param_shadowing(tmp_path):
    (tmp_path / "config.py").write_text(
        "import os\n\n"
        'API_KEY = os.getenv("API_KEY", "")\n\n\n'
        "def f(API_KEY, /):\n"
        "    return API_KEY\n"
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    secrets = {s.id: s for s in ast_scanner.scan_secrets(tmp_path, parsed)}
    assert secrets["secret.api_key"].in_context is False


def test_scan_secrets_in_context_ignores_shadow_in_outer_closure(tmp_path):
    """El shadow puede estar en un scope intermedio (no el mas interno): una funcion
    anidada que lee un nombre shadowed por la funcion que la contiene, no por si misma."""
    (tmp_path / "config.py").write_text(
        "import os\n\n"
        'API_KEY = os.getenv("API_KEY", "")\n\n\n'
        "def outer():\n"
        '    API_KEY = "shadowed-in-outer-not-a-secret"\n\n'
        "    def inner():\n"
        "        print(API_KEY)\n\n"
        "    inner()\n"
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    secrets = {s.id: s for s in ast_scanner.scan_secrets(tmp_path, parsed)}
    assert secrets["secret.api_key"].in_context is False


def test_scan_secrets_in_context_true_for_genuine_closure_reference(tmp_path):
    """Guardia de regresion: un closure de 2 niveles que SI lee el secreto real (sin
    shadow en ningun nivel intermedio) debe seguir contando como evidencia valida."""
    (tmp_path / "config.py").write_text(
        "import os\n\n"
        'API_KEY = os.getenv("API_KEY", "")\n\n\n'
        "def outer():\n"
        "    def inner():\n"
        "        return f\"key: {API_KEY}\"\n\n"
        "    return inner()\n"
    )
    parsed = ast_scanner.parse_repo(tmp_path)
    secrets = {s.id: s for s in ast_scanner.scan_secrets(tmp_path, parsed)}
    assert secrets["secret.api_key"].in_context is True
