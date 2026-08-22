.PHONY: api dashboard fixtures verify seed reset test

api:            ## Levanta el backend en :8000
	.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir services/api

fixtures:       ## Regenera fixtures/ desde el generador de referencia
	python3 protocol/gen_fixtures.py

verify:         ## Verifica los fixtures contra el verificador de referencia
	python3 protocol/verify.py

seed:           ## Carga los fixtures en el backend
	./demo/seed.sh

reset:          ## Vacía el incidente
	./demo/reset.sh

test: verify    ## Suite del núcleo
	@echo "OK"
