import argparse
import logging
import os

import pandoc
from xdg import xdg_cache_home, xdg_config_home

from .editor import Editor
from .googleapi import GoogleApiService
from .pandoc import pandoc_to_task_lists, task_lists_to_pandoc


def main():
    args = parse_args()

    config_dir = f"{xdg_config_home()}/gtasks-md/{args.user}/"
    os.makedirs(os.path.dirname(config_dir), exist_ok=True)
    cache_dir = f"{xdg_cache_home()}/gtasks-md/{args.user}/"
    os.makedirs(os.path.dirname(cache_dir), exist_ok=True)

    logging.basicConfig(
        filename=f"{xdg_cache_home()}/gtasks-md/log.txt",
        format="%(asctime)s %(levelname)-8s %(message)s",
        encoding="utf-8",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    match args.subcommand:
        case "auth":
            service = GoogleApiService(args.user)
            auth(service, args.credentials_file)
        case "edit":
            service = GoogleApiService(args.user)
            editor = Editor(args.editor)
            edit(service, editor)
        case "reconcile":
            service = GoogleApiService(args.user)
            reconcile(service, args.file_path)
        case "view":
            service = GoogleApiService(args.user)
            view(service)
        case None:
            print("Please run one of the subcommands.")


def parse_args():
    # https://stackoverflow.com/a/49977713
    parser = argparse.ArgumentParser(description="Google Tasks declarative management.")
    parser.add_argument(
        "--user",
        dest="user",
        default="default",
        help="Account for which the credentials are sourced. Should match desired Google account.",
        type=str,
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    auth = subparsers.add_parser("auth", help="Authorize.")
    auth.add_argument(
        "credentials_file",
        help="Location of credential file.",
        type=str,
    )

    subparsers.add_parser("view", help="View Google Tasks.")

    edit_parser = subparsers.add_parser("edit", help="Edit Google Tasks.")
    edit_parser.add_argument(
        "--editor",
        dest="editor",
        default="",
        help="Editor to be used for editing tasks. Defaults to $EDITOR and then $VISUAL and then vim.",
        type=str,
    )

    reconcile_parser = subparsers.add_parser(
        "reconcile", help="Patch tasklists with an offline source."
    )
    reconcile_parser.add_argument(
        "file_path",
        help="Location of the source file.",
        type=str,
    )

    return parser.parse_args()


def auth(service: GoogleApiService, file: str):
    with open(file, "r") as src_file:
        service.save_credentials(src_file.read())


def view(service: GoogleApiService):
    _, text = fetch_task_lists(service)
    print(text)


def edit(service: GoogleApiService, editor: Editor):
    old_task_lists, old_text = fetch_task_lists(service)
    new_text = editor.edit(old_text)
    new_task_lists = pandoc_to_task_lists(pandoc.read(new_text))
    service.reconcile(old_task_lists, new_task_lists)


def reconcile(service: GoogleApiService, file_path: str):
    old_task_lists, _ = fetch_task_lists(service)
    with open(file_path, "r") as source:
        new_text = source.read()
        new_task_lists = pandoc_to_task_lists(pandoc.read(new_text))
        service.reconcile(old_task_lists, new_task_lists)


def fetch_task_lists(service: GoogleApiService):
    task_lists = service.get_task_lists()
    doc = task_lists_to_pandoc(task_lists)
    return task_lists, pandoc.write(doc)


if __name__ == "__main__":
    main()