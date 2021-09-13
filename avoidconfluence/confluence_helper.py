import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from atlassian import Confluence
from atlassian.errors import ApiError, ApiValueError
from requests.exceptions import HTTPError


class ConfluenceHandler(object):
    """ """

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        space: str,
        dashboard: str,
        sync_up: bool = False,
    ) -> None:
        """ """
        self._space = space
        self._dashboard = dashboard

        self.c = Confluence(url=url, username=username, password=password)
        all_pages_from_space = self.c.get_all_pages_from_space(self._space)
        all_content_id_and_title = [
            (i.get("id"), i.get("title")) for i in all_pages_from_space
        ]
        confluence_page_metadata_list = []
        uuid_to_page_id = {}
        for id_, title in all_content_id_and_title:
            confluence_page_metadata = {
                "title": title,
                "confluence_id": id_,
                "uuid": None,
                "file_path": None,
            }
            try:
                uuid, file_path = self.c.get_page_property(id_, "uuid").get(
                    "value", None
                )
                if uuid:
                    uuid_to_page_id[uuid] = (id_, file_path)
                    confluence_page_metadata["uuid"] = uuid
                    confluence_page_metadata["file_path"] = file_path
            except ApiError:
                pass
            except HTTPError:
                pass
            confluence_page_metadata_list.append(confluence_page_metadata)
        self.uuid_to_page_id = uuid_to_page_id

        sync_metadata_path = Path(".av-metadata.json")
        if sync_up and sync_metadata_path.is_file():
            try:
                sync_metadata = json.load(sync_metadata_path.open())
            except Exception as e:
                raise ValueError(
                    f"[WARNING] Invalid '{sync_metadata_path}' file!\n{e}"
                )

            for user_sync_metadata in sync_metadata:
                if user_sync_metadata.get("uuid") and user_sync_metadata.get(
                    "file_path"
                ):
                    page_id = user_sync_metadata.get("confluence_id")
                    file_path = user_sync_metadata.get("file_path")
                    uuid = user_sync_metadata.get("uuid")
                    online_page_metadata = self.uuid_to_page_id.get(uuid)
                    print(f" * checking metadata upsteam for {uuid}..!")
                    if online_page_metadata:
                        online_page_id, online_file_path = online_page_metadata
                        if not (
                            online_page_id == page_id
                            and online_file_path == file_path
                        ):
                            self.c.delete_page_property(
                                page_id, "uuid"
                            )  # TODO revist this feature
                            self.c.set_page_property(
                                page_id,
                                {"key": "uuid", "value": (uuid, file_path)},
                            )
                            self.uuid_to_page_id[uuid] = (page_id, file_path)
                            print("  ! updated metadata upsteam")
                    else:
                        try:
                            self.c.delete_page_property(
                                page_id, "uuid"
                            )  # TODO is it required?
                        except Exception:
                            pass
                        finally:
                            self.c.set_page_property(
                                page_id,
                                {"key": "uuid", "value": (uuid, file_path)},
                            )

                        # self.uuid_to_page_id[uuid] = (page_id, file_path)
                        print("  + metadata upstream")

        if sync_up:
            with open(sync_metadata_path, "w") as f:
                save_metadata = [
                    metadata
                    for metadata in confluence_page_metadata_list
                    if not metadata.get("uuid")
                ]
                json.dump(save_metadata, f, indent=2)
            print(
                f"[INFO] saved metadata of {len(save_metadata)} unsynced pages to '{sync_metadata_path}'"
            )
        else:
            if sync_metadata_path.is_file():
                sync_metadata_path.unlink()

        print(
            f"[INFO] {len(self.uuid_to_page_id)}/{len(confluence_page_metadata_list)} pages is synced upsteam!"
        )
        print("-" * 69, "\n")

    def push(self, file_parts: Tuple[str, ...], metadata: dict) -> None:
        """ """
        root_name = self._dashboard
        title = metadata.get("title")
        body = metadata.get("body")
        uuid = metadata.get("uuid")
        file_path = metadata.get("file_path")
        labels = metadata.get("labels", [])
        attachment_data = metadata.get("attachment_data")

        print(f"[CONFLUENCE] '{title}'")
        length_of_file_parts = len(file_parts)
        for idx, part in enumerate(file_parts):
            parent_id = self.c.get_page_id(self._space, root_name)

            if length_of_file_parts == idx + 1:
                self.add_content(
                    parent_id=parent_id,
                    uuid=uuid,
                    file_path=file_path,
                    title=title,
                    body=body,
                    labels=labels,
                    attachment_data=attachment_data,
                )
                print(f'\n{"."*30} *DONE* {"."*30}\n')
            else:
                self.add_dir(dir_name=part, parent_id=parent_id)
                print(f" + {part}/")
                root_name = part

    def add_dir(self, dir_name: str, parent_id: int) -> int:
        """ """
        self.c.update_or_create(
            parent_id=parent_id,
            title=dir_name,
            body=f"{{children:reverse=true|sort=creation|style=h4|page={dir_name}|excerpt=none|first=99|depth=2|all=true}}",  # noqa
            representation="wiki",
        )
        return parent_id

    def attach_file(
        self, page_id: int, attachment_data: Dict[str, str]
    ) -> None:
        """ """

        for name, filename in attachment_data.items():
            try:
                self.c.attach_file(filename, name=name, page_id=page_id)
                print(f" + '{filename}' attachment")
            except FileNotFoundError:
                print(
                    f" [WARNING] `{name} attachment is not found at '{filename}'"
                )
            except Exception as e:
                print(f" [WARNING] `{name} attachment failed due to:\n{e}")

    def update_labels(self, page_id: int, labels: List[str]) -> None:
        """ """
        labels_list = self.c.get_page_labels(page_id).get("results", [])
        labels_list = [i.get("name") for i in labels_list]
        print(f"  = labels upstream: {labels_list}")
        for label_p in labels_list:
            if label_p not in labels:
                if isinstance(label_p, str):
                    self.c.remove_page_label(page_id, label_p)
                    print(f"  - {label_p} label")
        for label in labels:
            if label not in labels_list:
                if isinstance(label, str):
                    self.c.set_page_label(page_id, label)
                    print(f"  + {label} label")

    def add_content(
        self,
        parent_id: int,
        uuid: str,
        file_path: str,
        title: str,
        body: str,
        labels: List[str] = [],
        attachment_data: Optional[Dict[str, str]] = None,
    ) -> None:
        """ """

        if self.uuid_to_page_id.get(uuid):
            page_id, saved_file_path = self.uuid_to_page_id.get(uuid)
            print(
                "Debug uuid:",
                uuid,
                "\npage_id:",
                page_id,
                "\n saved_file_path:",
                saved_file_path,
            )
            print("Debug  file_path:", file_path)
            if saved_file_path != file_path:
                print(f" *mv* page {saved_file_path}")
                old_parent_id = self.c.get_parent_content_id(page_id)
                print("Debug id", old_parent_id, parent_id)
                self.c.move_page(
                    space_key=self._space,
                    page_id=page_id,
                    target_id=parent_id,
                    target_title=None,
                    position="append",
                )
                self.uuid_to_page_id[uuid] = (page_id, file_path)
                self.c.delete_page_property(
                    page_id, "uuid"
                )  # TODO use `update_page_property
                self.c.set_page_property(
                    page_id, {"key": "uuid", "value": (uuid, file_path)}
                )
                self.c.update_page(
                    page_id=page_id,
                    title=title,
                    body=body,
                    parent_id=parent_id,
                    type="page",
                    representation="wiki",
                    minor_edit=False,  # NOTE if false notification will be sent
                    version_comment=None,  # TODO get git commit message passed?
                    always_update=False,
                )

                print(
                    "Debug content",
                    self.c.get_subtree_of_content_ids(old_parent_id),
                )
                current_content_list = self.c.get_subtree_of_content_ids(
                    old_parent_id
                )
                if (
                    len(current_content_list) == 1
                    and old_parent_id in current_content_list
                ):
                    self.c.remove_page(old_parent_id)
                    print(
                        f"  - {old_parent_id}/"
                    )  # TODO get title of this page?

            else:
                print("  + push upsteam")
                self.c.update_page(
                    page_id=page_id,
                    title=title,
                    body=body,
                    parent_id=parent_id,
                    type="page",
                    representation="wiki",
                    minor_edit=False,  # NOTE if false notification will be sent
                    version_comment=None,  # TODO get git commit message passed
                    always_update=False,
                )
        else:
            print(f"  + new page")
            self.c.create_page(
                space=self._space,
                title=title,
                body=body,
                parent_id=parent_id,
                type="page",
                representation="wiki",
                editor=None,
            )
            page_id = self.c.get_page_id(self._space, title)
            try:
                self.c.set_page_property(
                    page_id, {"key": "uuid", "value": (uuid, file_path)}
                )
            except ApiValueError as e:
                print(e)

            # { "key" : "myprop", "value" :
            #   {
            #       "id": "507f1f77bcf86cd799439011",
            #       "editDate": "2000-01-01T11:00:00.000+11:00",
            #       "description": "If you have any questions please address them to admin@example.com",
            #       "content": {
            #           "likes": 5,
            #           "tags": ["cql", "confluence"]
            #       }
            #   }
            #  }

        print(
            "  = metadata",
            tuple(self.c.get_page_property(page_id, "uuid").get("value")),
        )

        if labels:
            self.update_labels(page_id, labels)

        if attachment_data:
            self.attach_file(page_id=page_id, attachment_data=attachment_data)
