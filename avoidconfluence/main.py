import argparse
import configparser
from pathlib import Path

from avoidconfluence.confluence_helper import ConfluenceHandler
from avoidconfluence.custom_modification import custom_extraction
from avoidconfluence.utils import get_metadata


def arg_parser():
    """ """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filenames",
        nargs="*",
        help="Filenames pre-commit believes are changed.",
    )
    parser.add_argument(
        "--input-format",
        nargs="*",
        default="org",
        help="Filenames format supported by pandon.",
    )
    parser.add_argument(
        "--toc",
        action="store_true",
        help="Enable table of content on the confluence page.",
    )
    parser.add_argument(
        "--sync-up",
        action="store_true",
        help="Get metadata for the confluence page to sync up.",
    )
    return parser.parse_args()


def update_space(
    url: str,
    username: str,
    password: str,
    space: str,
    dashboard: str,
    sync_up: bool,
    filenames: str,
    input_format: str,
    enable_toc: bool,
) -> None:
    """Force pushes the list of files to the configured confluences space."""
    supported_files = [".org", ".md"]
    confluence_obj = ConfluenceHandler(
        url=url,
        username=username,
        password=password,
        space=space,
        dashboard=dashboard,
        sync_up=sync_up,
    )

    for file_relative_path in filenames:
        file_obj = Path(file_relative_path)
        if (
            file_obj.suffix in supported_files
            and file_obj.is_file()
            and f".{input_format}" in supported_files
        ):
            try:
                metadata_obj = get_metadata(
                    file_path=file_relative_path,
                    file_name=file_obj.stem,
                    body=file_obj.read_text(),
                    input_format=input_format,
                )
                custom_extraction(
                    metadata=next(metadata_obj), enable_toc=enable_toc
                )
                confluence_obj.push(
                    file_parts=file_obj.parts, metadata=next(metadata_obj)
                )
            except Exception as e:
                print(
                    f"[ERROR] Failed to upload the '{file_relative_path}' to confluence due to:\n{e}"
                )
        else:
            print(
                f'[INFO] Skipped unsupported file \'{file_obj}\', Ensure the supported files ending with either of these \'{", ".join([i for i in supported_files])}\'\nSet the argument with the \'--input_format=md\' in \'.pre-commit-config.yaml\''
            )  # noqa


def main() -> None:
    """Entry ponint for the avoid confluence script."""
    args = arg_parser()

    if isinstance(args.input_format, str):
        input_format = args.input_format
    elif isinstance(args.input_format, list) and len(args.input_format) == 1:
        input_format = args.input_format[0]
    else:
        raise ValueError("Invalid --input_format argument.")

    config = configparser.ConfigParser()
    config.read(".av-config.ini")

    update_space(
        url=config["CONFLUENCE"]["URL"],
        username=config["CONFLUENCE"]["USERNAME"],
        password=config["CONFLUENCE"]["PASSWORD"],
        space=config["CONFLUENCE"]["SPACE"],
        dashboard=config["CONFLUENCE"]["CONFLUENCE_DASHBOARD"],
        sync_up=args.sync_up,
        filenames=args.filenames,
        input_format=input_format,
        enable_toc=args.toc,
    )


if __name__ == "__main__":
    main()
