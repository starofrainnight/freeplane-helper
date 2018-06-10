#!/usr/bin/env python3

import os
import os.path
import click
import shutil
import subprocess
import re
from whichcraft import which
from rabird.core.configparser import ConfigParser


def fp_get_user_dir():
    return os.path.expandvars(
        os.path.expanduser("~/.config/freeplane/1.6.x"))


def fp_ensure_script_executable():
    user_dir = fp_get_user_dir()

    properties_path = os.path.join(user_dir, 'auto.properties')
    if not os.path.exists(properties_path):
        return

    with open(properties_path, 'r') as f:
        cfgparser = ConfigParser()
        cfgparser.readfp(f)

    # Change settings if they not set correctly
    settings = {
        "execute_scripts_without_network_restriction": "true",
        "execute_scripts_without_write_restriction": "true",
        "execute_scripts_without_exec_restriction": "true",
        "execute_scripts_without_asking": "true",
        "execute_scripts_without_file_restriction": "true",
    }

    modified = False
    section = ConfigParser.UNNAMED_SECTION
    for k, v in settings.items():
        if cfgparser.get(section, k) != v:
            cfgparser.set(section, k, v)
            modified = True

    if modified:
        # Backup old
        properties_bak_path = properties_path + '.bak'
        try:
            os.remove(properties_bak_path)
        except:
            pass

        shutil.copyfile(properties_path, properties_bak_path)

        with open(properties_path, 'w') as f:
            cfgparser.write(f, space_around_delimiters=False)


def fp_fix_markdown_title(lines):
    first_line = lines[0]
    if len(first_line) <= 0:
        return

    if not re.match(r'\s+.*', first_line):
        return

    # Fixs title
    lines[0] = '%' + first_line


def fp_fix_markdown_references(lines):
    for i in range(0, len(lines)):
        line = lines[i]

        if not re.match(r'\s+\(see:.*', line):
            continue

        lines[i] = line + '\n'


def fp_fix_markdown(md_doc):
    """Freeplane generated markdown format have some issues:

    1. Title not been correctly generated
    2. Linked nodes will snap to next section, that lead pandoc failed to
    generate correct table of contents
    """

    with open(md_doc, 'r') as f:
        lines = f.readlines()

    if len(lines) <= 0:
        return

    fp_fix_markdown_title(lines)
    fp_fix_markdown_references(lines)

    with open(md_doc, 'w') as f:
        f.write(''.join(lines))


@click.command()
@click.argument('fp_doc')
def main(fp_doc):
    """A script to convert Freeplane document to Markdown correctly.
    """

    fp_ensure_script_executable()

    # Copy groovy export script for Freeplane
    scripts_dir = os.path.join(fp_get_user_dir(), 'scripts')
    shutil.copy(
        os.path.join(os.path.dirname(__file__),
                     'scripts', 'ExportToMarkdown.groovy'),
        scripts_dir)

    fp_binary = which('freeplane')

    subprocess.call(
        [fp_binary, '-S', '-N', '-XExportToMarkdown_on_selected_node', fp_doc])

    md_doc = (
        os.path.splitext(os.path.basename(fp_doc))[0] + '.md')

    fp_fix_markdown(md_doc)

    # TODO: Seems my pandoc on Ubuntu 18.04 too old to generate the PDF from
    # markdown file. If you want to generate a correctly PDF file, you must
    # use pandoc to convert this markdown file to odt file, then use libreoffice
    # to fix the section numbers issue, finally generate PDF by libreoffice.


if __name__ == '__main__':
    main()
