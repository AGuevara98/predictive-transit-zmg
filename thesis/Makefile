# Thesis build. Requires `tectonic` on PATH (single-binary LaTeX engine) and the
# repo virtualenv for figure regeneration.
#
#   make figures   regenerate all figures from the DB + outputs/ CSVs
#   make en        build the English PDF   (en/main.pdf)
#   make es        build the Spanish PDF   (es/main.pdf)
#   make all       figures + both PDFs
#   make clean     remove build artifacts

PY  ?= ../.venv/bin/python
TECTONIC ?= tectonic
export LC_ALL = C.UTF-8
# tectonic commonly installs to ~/.local/bin, which non-interactive recipe shells
# may not have on PATH; prepend it (harmless if tectonic lives elsewhere).
export PATH := $(HOME)/.local/bin:$(PATH)

.PHONY: all en es figures clean

# Build both PDFs from the committed figures (no DB needed).
all: en es

# Regenerate figures from the live DB + outputs/ CSVs (opt-in; needs the repo venv
# and the gdl_metro DB up). Run this after a pipeline re-run, then `make all`.
figures:
	$(PY) figures_src/make_thesis_figures.py

en:
	cd en && $(TECTONIC) main.tex

es:
	cd es && $(TECTONIC) main.tex

clean:
	rm -f en/main.pdf es/main.pdf
	rm -f */*.aux */*.bbl */*.bcf */*.blg */*.log */*.out */*.toc */*.lof */*.lot */*.run.xml
