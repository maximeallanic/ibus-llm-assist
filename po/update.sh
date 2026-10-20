#!/usr/bin/env bash
# Regenerates po/ibus-llm-assist.pot from the sources and merges it into every po/<lang>.po.
# Run after changing a user-facing string; tests/test_i18n.py fails while the template is out of date.
set -euo pipefail
cd "$(dirname "$0")/.."
xgettext --from-code=UTF-8 --add-comments=TRANSLATORS --package-name=ibus-llm-assist --package-version=0.1.1 --copyright-holder="Maxime Allanic" --sort-by-file \
    --msgid-bugs-address=https://github.com/maximeallanic/ibus-llm-assist/issues \
    -o po/ibus-llm-assist.pot.new -L Python --keyword=_ --keyword=ngettext:1,2 llm_assist/*.py
xgettext --from-code=UTF-8 -j -o po/ibus-llm-assist.pot.new -L Shell --keyword=t --keyword=tf \
    install.sh uninstall.sh verify.sh lib/*.sh
xgettext --from-code=UTF-8 -j -o po/ibus-llm-assist.pot.new data/io.github.maximeallanic.IBusLlmAssist.gschema.xml
# xgettext's -j runs keep the placeholder header: fill it in.
sed -i -e '1,4c\# Translations of ibus-llm-assist.\n# Copyright (c) 2026 Maxime Allanic\n# This file is distributed under the same license as ibus-llm-assist (MIT).\n#' \
    -e 's/^"Project-Id-Version: PACKAGE VERSION/"Project-Id-Version: ibus-llm-assist 0.1.1/' \
    -e 's|^"Report-Msgid-Bugs-To: \\n"|"Report-Msgid-Bugs-To: https://github.com/maximeallanic/ibus-llm-assist/issues\\n"|' \
    po/ibus-llm-assist.pot.new
# The creation date changes on every run: keep the old template when nothing else did.
if [ -f po/ibus-llm-assist.pot ] && diff -q -I '^"POT-Creation-Date' po/ibus-llm-assist.pot po/ibus-llm-assist.pot.new >/dev/null; then
    rm po/ibus-llm-assist.pot.new
else
    mv po/ibus-llm-assist.pot.new po/ibus-llm-assist.pot
fi
for po in po/*.po; do
    [ -f "$po" ] || continue
    msgmerge --quiet --update --backup=none --no-fuzzy-matching "$po" po/ibus-llm-assist.pot
done
