import re
from pathlib import Path
from typing import Dict, List, Union


def custom_extraction(metadata, enable_toc=False):
    """ """
    jira_body = metadata["body"]

    replacement_list = [
        ("&hyphen;", "-", "* fix Hyphen ."),
        ("&lowbar;", "_", "* fix Underscore ."),
        ("&commat;", "@", "* fix At symbol ."),
        ("&plus;", "+", "* fix Plus symbol ."),
        ("&quot;", '"', "* fix Quot symbol ."),
        ("&gt;", ">", "* fix > symbol ."),
        ("&lt;", "<", "* fix < symbol ."),
        ("&ast;", "*", "* fix * symbol ."),
        ("&vert;", "/", "* fix / symbol ."),
        ("[ ]", "☐", "* fix Check box Todo ."),
        ("[X]", "☑", "* fix Check box Done ."),
    ]

    for org_src, modified_src, msg in replacement_list:
        print(msg)
        jira_body = jira_body.replace(org_src, modified_src)

    print("  * fix images absolute path .")
    jira_body = check_for_full_path_images(jira_body)

    print("  * fix images relative path .")
    try:
        image_attachment_metadata = {}
        (jira_body, image_attachment_metadata) = fix_path_for_images_to_upload(
            jira_body
        )
    except:
        pass

    print("  * get file for attachment .")
    jira_body, file_attachment_metadata = check_for_attachments_files(
        jira_body
    )

    file_attachment_metadata.update(image_attachment_metadata)

    print("  * fix page link .")
    jira_body = fix_page_link(jira_body)

    print("  * checking for table of content .")
    jira_body = "{toc}\n" + jira_body if enable_toc else jira_body

    file_attachment_metadata = (
        file_attachment_metadata if file_attachment_metadata else None
    )

    metadata["body"] = jira_body
    metadata["attachment_data"] = file_attachment_metadata

    return metadata


# def get_title(body):
#     start_pattern = '#\+title:'
#     end_pattern = '#\+date:'
#
#     x = re.search(f'{start_pattern}[\w\S\D]+{end_pattern}',
#                   body)
#
#     start, end = x.span()
#     start += len(start_pattern)
#     end -=len(end_pattern)
#
#     return body[start:end]


def fix_page_link(body):
    """ """
    import os

    possible_notes = [
        Path(f).stem
        for _, _, files in os.walk(".")
        for f in files
        if f.endswith(".org")  # TODO Lower
    ]

    def get_fixed_title(file_marker):
        file_marker = file_marker[1:-1].replace("^~", "_")
        for file_notes in possible_notes:
            print(file_marker, file_notes)
            if file_marker in file_notes:
                _, _, title = file_notes.split("--")
                title = title.replace("-", " ")
                title = title.replace("_", "-")
                title = title.capitalize()
                return f"[{title}]"

    page_link: Dict[str, str] = {}
    for i in re.finditer("\^\d{8}\^~\d{6}~", body):
        page_s_idx, page_e_idx = i.span()
        page_match = body[page_s_idx:page_e_idx]
        if not page_link.get(page_match):
            page_link[page_match] = get_fixed_title(page_match)

    for k, v in page_link.items():
        v = v if isinstance(v, str) else ""
        body = body.replace(k, v)
    return body


def check_for_full_path_images(body):
    """ """
    ignore_path_prefix = ["[[", "file:"]
    full_path_image_metadata = {}

    for k, v in zip(
        re.finditer("!\|[\w\d\S]+\]", body),
        re.finditer("\[![\w\S\D]+!\|", body),
    ):

        k_s_idx, k_e_idx = k.span()
        v_s_idx, v_e_idx = v.span()
        file_path_full_syntax = body[v_s_idx:k_e_idx]

        file_s_idx = k_s_idx + 2
        file_e_idx = k_e_idx - 1
        file_path = body[file_s_idx:file_e_idx]

        for i in ignore_path_prefix:
            if file_path.startswith(i):
                file_path = file_path[len(i) :]

        to_replace_with = f"!{file_path}!"
        full_path_image_metadata[file_path_full_syntax] = to_replace_with
    # replace the syntax
    for k, v in full_path_image_metadata.items():
        body = body.replace(k, v)
    return body


def fix_path_for_images_to_upload(body):
    """ """
    image_attachment_metadata = {}
    images_name_to_replace = {}
    root_path = None

    for i in re.finditer("![\w\S\D]+?!", body):
        s, e = i.span()

        file_path_syntax = body[s:e]
        file_path = body[s + 1 : e - 1]
        file_obj = Path(file_path)
        if file_path.startswith("~/"):
            file_obj = file_obj.expanduser()
        elif root_path:
            file_obj = Path(root_path).joinpath(file_obj)

        if file_obj.is_file():
            images_name_to_replace[file_path_syntax] = f"!{file_obj.name}!"
            image_attachment_metadata[file_obj.name] = str(file_obj)

    for k, v in images_name_to_replace.items():
        body = body.replace(k, v)
    return body, image_attachment_metadata


def check_for_attachments_files(body):
    """ """
    file_name_prefix_ignore = ["[[", "file:"]
    attachment_metadata = {}

    for i in re.finditer("\[\[[\w\S\D]+?\]\|[\w\S\D]+?\]", body):
        s, e = i.span()
        file_attachment_syntax = body[s:e]
        # print(body[s:], '\n--\n')
        # print('Match object:', i, '\n',
        #       '--'*20, '\n',
        #       'Match:', file_attachment_syntax, '\n'
        #       '**'*15)
        file_name, file_path_to_upload = file_attachment_syntax.split("]|")
        file_path_to_upload = file_path_to_upload[:-1]
        for i in file_name_prefix_ignore:
            if file_name.startswith(i):
                file_name = file_name[len(i) :]

        file_obj = Path(file_path_to_upload)
        if file_path_to_upload.startswith("~/"):
            file_obj = file_obj.expanduser()

        filename_to_attach = Path(file_name).name
        attachment_metadata[filename_to_attach] = str(file_obj)
        # print(filename_to_attach)
        # print(file_path_to_upload)
        body = body.replace(file_attachment_syntax, f"[^{filename_to_attach}]")
    return body, attachment_metadata
