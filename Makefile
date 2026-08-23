.PHONY: bootstrap proto test sim up lint arch-check apk alert-ingestor

# Instala dependencias y prepara el entorno (Gradle wrapper, venv de servicios, node_modules web)
bootstrap:
	./gradlew --version
	python3 -m venv services/alert_ingestor/.venv
	services/alert_ingestor/.venv/bin/pip install -e "services/alert_ingestor[dev]"
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
	services/alert_ingestor/.venv/bin/pytest services/alert_ingestor -q
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
	services/alert_ingestor/.venv/bin/ruff check services/alert_ingestor
	@echo "TODO(dueño=Miguel): ruff check en el resto de services/"
	@echo "TODO(dueño=Miguel): npm run lint --prefix web"

# Verifica reglas de arquitectura hexagonal (arch-guard: Konsist + import-linter)
arch-check:
	./gradlew konsistCheck
	services/alert_ingestor/.venv/bin/lint-imports

# Corre el worker de ingesta de alertas sísmicas (EMSC + USGS) en bucle
alert-ingestor:
	services/alert_ingestor/.venv/bin/python -m alert_ingestor.bootstrap.main

# Genera el APK de debug del módulo android/app
apk:
	./gradlew :android:app:assembleDebug
