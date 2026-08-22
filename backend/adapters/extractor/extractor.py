"""PyAstExtractor — adaptador real de ArchitectureExtractorPort (D1).

MVP (specs/02-architecture-ports.md, specs/03-components.md #C1): `ast` nativo para el
grafo (un solo parseo por archivo, reusado entre todos los scan_*) + 1 regla Semgrep de
corroboracion (subprocess/os.system con shell=True, con fallback si no esta instalado) +
1 pasada LLM opcional para refinar side_effects/trust_level/descripciones.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from adapters.extractor import ast_scanner, llm_enrich, semgrep_scan
from contracts import AgentArchitecture, Tool

logger = logging.getLogger(__name__)


class PyAstExtractor:
    """Implementa ArchitectureExtractorPort (domain/ports.py)."""

    def extract(self, repo_path: str) -> AgentArchitecture:
        root = Path(repo_path).resolve()
        parsed = ast_scanner.parse_repo(root)
        entrypoint = ast_scanner.find_entrypoint(root, parsed)

        tools = ast_scanner.scan_tools(root, parsed)
        # Pydantic valida en la construccion (regla del contrato: "el productor valida
        # antes de escribir" — specs/01-data-contracts.md); un campo invalido revienta aca.
        arch = AgentArchitecture(
            agent=ast_scanner.scan_agent_info(root, entrypoint, parsed),
            tools=tools,
            mcp_servers=ast_scanner.scan_mcp_servers(root, parsed),
            data_flows=ast_scanner.scan_data_flows(root, parsed, tools),
            secrets=ast_scanner.scan_secrets(root, parsed),
            rag=ast_scanner.scan_rag(root, parsed),
            agent_loop=ast_scanner.scan_agent_loop(parsed),
        )

        hits = semgrep_scan.run_semgrep(root)
        if hits is None:
            logger.warning("semgrep no disponible; extraccion continua solo con ast")
        else:
            logger.info("semgrep corroboro %d hallazgo(s) untrusted->sink", len(hits))
            self._warn_on_uncovered_sinks(root, parsed, tools, arch, hits)

        return llm_enrich.enrich(arch)

    @staticmethod
    def _warn_on_uncovered_sinks(
        root: Path,
        parsed: list[ast_scanner.ParsedFile],
        tools: list[Tool],
        arch: AgentArchitecture,
        hits: list[dict],
    ) -> None:
        """Si semgrep marco un sink peligroso dentro de una tool para la que ast NO logro
        vincular ningun data_flow, avisa puntualmente -- ast pudo perder el patron de taint
        (p.ej. una f-string), pero el sink sigue siendo real segun semgrep.
        """
        covered = {f.sink.at for f in arch.data_flows}
        for hit in hits:
            hit_path_raw = hit.get("path")
            hit_line = hit.get("start", {}).get("line")
            if not hit_path_raw or hit_line is None:
                continue
            hit_path = Path(hit_path_raw)
            for tool_id in ast_scanner.tools_containing_line(root, parsed, hit_path, hit_line, tools):
                tool = next(t for t in tools if t.id == tool_id)
                if tool.defined_at not in covered:
                    logger.warning(
                        "semgrep encontro un sink peligroso en %s (%s) que ast no vinculo a "
                        "ningun data_flow user_input->sink -- revisar manualmente",
                        tool.id,
                        tool.defined_at,
                    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m adapters.extractor")
    parser.add_argument("repo_path", help="ruta al repo del agente objetivo")
    parser.add_argument("--out", help="si se pasa, escribe architecture.json en esta ruta")
    args = parser.parse_args(argv)

    arch = PyAstExtractor().extract(args.repo_path)
    payload = arch.model_dump_json(indent=2)
    if args.out:
        Path(args.out).write_text(payload + "\n")
        print(f"architecture.json escrito en {args.out}")
    else:
        print(payload)


if __name__ == "__main__":
    main()
