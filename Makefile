.PHONY: bootstrap proto test sim up lint arch-check apk

# Instala dependencias y prepara el entorno (Gradle wrapper, venv de servicios, node_modules web)
bootstrap:
	./gradlew --version
	@echo "TODO(dueño=Miguel): bootstrap de venv Python por servicio (services/*)"
	@echo "TODO(dueño=Miguel): npm install en web/"

# Regenera código a partir de protocol/proto/**/*.proto (Kotlin, Python, TypeScript) y detecta drift
proto:
	bash protocol/codegen/gen_kotlin.sh
	bash protocol/codegen/gen_python.sh
	bash protocol/codegen/gen_ts.sh

# Corre toda la batería de tests (core en JVM, servicios con pytest, web con vitest)
test:
	./gradlew test
	@echo "TODO(dueño=Miguel): pytest en services/"
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
	@echo "TODO(dueño=Miguel): ruff check services/"
	@echo "TODO(dueño=Miguel): npm run lint --prefix web"

# Verifica reglas de arquitectura hexagonal (arch-guard: Konsist + import-linter)
arch-check:
	./gradlew konsistCheck
	@echo "TODO(dueño=Miguel): lint-imports (.importlinter)"

# Genera el APK de debug del módulo android/app
apk:
	./gradlew :android:app:assembleDebug
