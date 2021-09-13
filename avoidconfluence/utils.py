from pathlib import Path
from typing import Any, Dict, Iterator, List, Union

from avoidconfluence.pandoc_jira import get_jira_markup


def fix_title(title):
    title = title.replace("-", " ")
    title = title.replace("_", "-")
    title = title.capitalize()
    return title


def get_metadata(
    file_path: str, file_name: str, body: str, input_format: str
) -> Any:
    # ) -> Iterator[Dict[str, Union[str, List[str]]]]:
    """ """
    print(f"[LOCAL File] '{file_path}'")

    split_body = body.split("#+include: ")

    if len(split_body) > 1:
        new_body, *rest_half = split_body
        for i in rest_half:
            include_file_path, *end_of_body = i.split("\n")
            include_file_path = include_file_path.strip()
            include_file = Path(include_file_path).expanduser()
            if include_file.is_file():
                new_body += include_file.read_text()
            new_body += "\n".join(end_of_body)
        body = new_body

    jira_body = get_jira_markup(source=body, input_format=input_format)

    metadata: Dict[str, Union[str, List[str]]] = {
        "file_path": file_path,
        "body": jira_body,
        "title": None,
        "uuid": None,
        "labels": None,
        "attachment_data": None,
    }
    yield metadata  # NOTE Users get to change the metadat to their linking

    if metadata.get("uuid") and metadata.get("title"):
        yield metadata  # NOTE if uuid and title not set use the defaut method

    if len(file_name.split("--")) != 3:
        raise ValueError(
            f"[WARNING] Expected file format is {{uuid}}--{{label}}--{{titles}} but given {file_name}"
        )  # noqa

    print("  * append metadata .")
    uuid, labels, title = file_name.split("--")

    metadata["title"] = fix_title(title)
    metadata["uuid"] = uuid

    if not metadata.get("labels"):
        metadata["labels"] = labels.split("-")

    yield metadata
