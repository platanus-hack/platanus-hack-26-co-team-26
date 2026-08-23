.PHONY: bootstrap proto test sim up lint arch-check apk found-persons

# Instala dependencias y prepara el entorno (Gradle wrapper, venv de servicios, node_modules web)
bootstrap:
	./gradlew --version
	python3 -m venv services/found_persons/.venv
	services/found_persons/.venv/bin/pip install -e "services/found_persons[dev]"
	@echo "TODO(dueño=Miguel): venv para el resto de services/*"
	@echo "TODO(dueño=Miguel): npm install en web/"

# Regenera código a partir de protocol/proto/**/*.proto (Kotlin, Python, TypeScript) y detecta drift
proto:
	bash protocol/codegen/gen_kotlin.sh
	bash protocol/codegen/gen_python.sh
	bash protocol/codegen/gen_ts.sh

# Corre toda la batería de tests (core en JVM, servicios con pytest, web con vitest)
test:
	./gradlew test
	services/found_persons/.venv/bin/pytest services/found_persons -q
	@echo "TODO(dueño=Miguel): pytest en el resto de services/"
	@echo "TODO(dueño=Miguel): npm test en web/"

# Levanta simulators/mesh_sim con N nodos hablando el protocolo real
sim:
	@echo "TODO(dueño=Miguel): ./gradlew :simulators:mesh_sim:run --args=\"--nodes=10 --rubble-model=default\""

# Levanta el stack local completo (backend, Postgres/PostGIS, Redis, MinIO)
up:
	docker compose -f docker-compose.yml up -d

# Lint completo: ktlint + detekt (Kotlin), ruff/black (Python), eslint (TypeScript)
lint:
	./gradlew ktlintCheck detekt
	services/found_persons/.venv/bin/ruff check services/found_persons
	@echo "TODO(dueño=Miguel): ruff check en el resto de services/"
	@echo "TODO(dueño=Miguel): npm run lint --prefix web"

# Verifica reglas de arquitectura hexagonal (arch-guard: Konsist + import-linter)
arch-check:
	./gradlew konsistCheck
	services/found_persons/.venv/bin/lint-imports

# Levanta solo la API de personas localizadas, sin el resto del stack
found-persons:
	services/found_persons/.venv/bin/uvicorn found_persons.bootstrap.main:app --reload --port 8010

# Genera el APK de debug del módulo android/app
apk:
	./gradlew :android:app:assembleDebug
