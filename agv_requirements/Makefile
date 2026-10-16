PY ?= python3

.PHONY: all figures site serve clean check

all: figures site

figures:            ## regenerate SVG figures + docs/AGV_requirements_illustrated.md
	$(PY) generator/build.py

site: figures       ## regenerate site/ from the markdown
	$(PY) sitegen/build_site.py

serve: site         ## preview at http://localhost:8000
	$(PY) -m http.server 8000 --directory site

check: all          ## fail if a rebuild changes committed output (use in CI)
	git diff --exit-code -- docs site

clean:
	rm -rf site
