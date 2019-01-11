#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Console script for freeplane-helper."""

import os
import os.path
import sys
import click
import shutil
import subprocess
import re
import pypandoc
import glob
from whichcraft import which
from rabird.core.configparser import ConfigParser


def get_supported_formats():
    return {
        "md": "Markdown syntax",
        "odt": "OpenDocument",
        "pdf": "Netware Printer Definition File. PDF (Portable Document Format)",  # noqa
    }


def search_cmd(cmd, mode=os.F_OK | os.X_OK, path=None):
    """Given a command, mode, and a PATH string, return the path which
    conforms to the given mode on the PATH, or None if there is no such
    file.
    `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
    of os.environ.get("PATH"), or can be overridden with a custom search
    path.
    Note: This function was backported from the Python 3 source code.
    """
    # Check that a given file can be accessed with the correct mode.
    # Additionally check that `file` is not a directory, as on Windows
    # directories pass the os.access check.

    def _access_check(fn, mode):
        return (
            os.path.exists(fn)
            and os.access(fn, mode)
            and not os.path.isdir(fn)
        )

    # If we're given a path with a directory part, look it up directly
    # rather than referring to PATH directories. This includes checking
    # relative to the current directory, e.g. ./script
    if os.path.dirname(cmd):
        if _access_check(cmd, mode):
            return cmd

        return None

    if path is None:
        path = os.environ.get("PATH", os.defpath)
    if not path:
        return None

    path = path.split(os.pathsep)

    if sys.platform == "win32":
        # The current directory takes precedence on Windows.
        if os.curdir not in path:
            path.insert(0, os.curdir)

        # PATHEXT is necessary to check on Windows.
        pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
        # See if the given file matches any of the expected path
        # extensions. This will allow us to short circuit when given
        # "python.exe". If it does match, only test that one, otherwise we
        # have to try others.
        if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
            files = [cmd]
        else:
            files = [cmd + ext for ext in pathext]
    else:
        # On other platforms you don't have things like PATHEXT to tell you
        # what file suffixes are executable, so just pass on cmd as-is.
        files = [cmd]

    seen = set()
    for dir in path:
        normdir = os.path.normcase(dir)
        if normdir not in seen:
            seen.add(normdir)
            cmd_pattern = os.path.join(dir, cmd)
            files = glob.glob(cmd_pattern)
            for thefile in files:
                name = os.path.join(dir, thefile)
                if _access_check(name, mode):
                    return name
    return None


def fp_get_user_dir():
    return os.path.expandvars(os.path.expanduser("~/.config/freeplane/1.6.x"))


def fp_ensure_script_executable():
    user_dir = fp_get_user_dir()

    properties_path = os.path.join(user_dir, "auto.properties")
    if not os.path.exists(properties_path):
        return

    with open(properties_path, "r") as f:
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
        properties_bak_path = properties_path + ".bak"
        try:
            os.remove(properties_bak_path)
        except OSError:
            pass

        shutil.copyfile(properties_path, properties_bak_path)

        with open(properties_path, "w") as f:
            cfgparser.write(f, space_around_delimiters=False)


def fp_fix_markdown_title(lines):
    first_line = lines[0]
    if len(first_line) <= 0:
        return

    if not re.match(r"\s+.*", first_line):
        return

    # Fixs title
    lines[0] = "%" + first_line


def fp_fix_markdown_references(lines):
    for i in range(0, len(lines)):
        line = lines[i]

        if not re.match(r"\s+\(see:.*", line):
            continue

        lines[i] = line + "\n"


def fp_markdown_add_section_numbers(lines):
    level_nums = []
    last_level = 0
    num = 1
    for i in range(0, len(lines)):
        line = lines[i]

        matched = re.match(r"\s*(#+)(.*)", line)
        if not matched:
            continue

        level = len(matched.group(1))

        if level == last_level:
            num += 1
        elif level > last_level:
            level_nums.append(num)
            last_level = level
            num = 1
        else:
            num = level_nums.pop()
            num = num + 1
            last_level = level

        # Convert to string list
        final_level_nums = level_nums[1:] + [num]
        final_level_nums = [str(num) for num in final_level_nums]

        line = "%s %s %s" % (
            matched.group(1),
            ".".join(final_level_nums),
            matched.group(2),
        )

        lines[i] = line + "\n"


def fp_fix_markdown(md_doc, is_gen_number_sections):
    """Freeplane generated markdown format have some issues:

    1. Title not been correctly generated
    2. Linked nodes will snap to next section, that lead pandoc failed to
    generate correct table of contents
    """

    with open(md_doc, "r") as f:
        lines = f.readlines()

    if len(lines) <= 0:
        return

    fp_fix_markdown_title(lines)
    fp_fix_markdown_references(lines)
    if is_gen_number_sections:
        fp_markdown_add_section_numbers(lines)

    with open(md_doc, "w") as f:
        f.write("".join(lines))


@click.group()
def main():
    """A script to convert Freeplane document to Markdown correctly.
    """
    pass


@main.command()
def list_formats():
    """List supported output formats

    """
    formats = get_supported_formats()
    for k, v in formats.items():
        click.echo("%s\t%s" % (k, v))


@main.command()
@click.argument("fp_doc")
@click.option(
    "-n", "--number-sections", is_flag=True, help="If generate number sections"
)
@click.option(
    "-f",
    "--format",
    type=click.Choice(get_supported_formats().keys()),
    default="odt",
    help="Output format, defaults to 'odt'",
)
def convert(fp_doc, number_sections, format):
    """Convert FreePlane document to specific format document"""

    fp_ensure_script_executable()

    # Copy groovy export script for Freeplane
    scripts_dir = os.path.join(fp_get_user_dir(), "scripts")
    shutil.copy(
        os.path.join(
            os.path.dirname(__file__), "scripts", "ExportToMarkdown.groovy"
        ),
        scripts_dir,
    )

    fp_binary = which("freeplane")

    subprocess.call(
        [fp_binary, "-S", "-N", "-XExportToMarkdown_on_selected_node", fp_doc]
    )

    md_doc = os.path.splitext(os.path.basename(fp_doc))[0] + ".md"

    fp_fix_markdown(md_doc, number_sections)

    # We only needs the markdown format output
    if "md" == format:
        return

    # Seems pandoc on Ubuntu 18.04 too old to generate the PDF from
    # markdown file. If you want to generate a correctly PDF file, you must
    # use pandoc to convert this markdown file to odt file, then use
    # libreoffice to fix the section numbers issue, finally generate PDF by
    # libreoffice.
    odt_doc = os.path.splitext(md_doc)[0] + ".odt"
    pypandoc.convert_file(md_doc, "odt", outputfile=odt_doc)

    # We only needs the odt format output
    if "odt" == format:
        return

    # Generate PDF by libreoffice

    # FIXME: We use a tricky way that add section numbers inside markdown for
    # generate section numbers of odt files, but the section numbers is
    # different from libreoffice's styled section number!
    libreoffice_cmd = search_cmd("libreoffice*")
    subprocess.call([libreoffice_cmd, "--convert-to", "pdf", odt_doc])


if __name__ == "__main__":
    main()
