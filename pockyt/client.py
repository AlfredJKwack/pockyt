from __future__ import absolute_import, print_function, unicode_literals, with_statement

import sys
import time
import json
from datetime import datetime
from os.path import join

import parse

from .api import API
from .compat import prompt
from .wrapper import Browser, FileSystem, Network


class Client(object):
    """
    Pocket API Access Client
    """
    def __init__(self, credentials, args):
        self._args = args
        self._credentials = credentials
        self._api_endpoint = ""
        self._payload = {}
        self._response = None

        self._format_spec = ""
        self._unformat_spec = None
        self._output = []
        self._input = []

    def _api_request(self):
        # add API access credentials
        self._payload.update(self._credentials)

        # access API
        self._response = Network.post_request(self._api_endpoint,
                                              self._payload)

    def _output_to_file(self):
        file_path = FileSystem.resolve_path(self._args.output)
        if self._args.output_json:
            content = json.dumps(self._output, indent=4, sort_keys=True)
        else:        
            content = "".join(
                map(lambda info: self._format_spec.format(**info), self._output))
        FileSystem.write_to_file(file_path, content)

    def _print_to_console(self, info):
        if self._args.output_json:
            print(json.dumps(info, indent=4, sort_keys=True))
        else:
            line = self._format_spec.format(**info)
            try:
                print(line, end="")
            except UnicodeEncodeError:
                print(line.encode(API.ENCODING), end="")

    def _open_in_browser(self, info):
        time.sleep(1)
        Browser.open_new_tab(info["link"])

    def _save_to_archive(self, info):
        archive_path = FileSystem.resolve_path(self._args.archive)
        FileSystem.ensure_dir((archive_path))
        title = FileSystem.get_safe_name(info["title"])
        filename = "{0} - {1}.html".format(info["id"], title)
        filepath = join(archive_path, filename)
        html = Network.get_html(info["link"])
        FileSystem.write_to_file(filepath, html)

    def _get_console_input(self):
        print("Enter data: {0}".format(self._args.format.strip()))
        try:
            while True:
                data = prompt().strip()
                if data:
                    info = self._unformat_spec.parse(data)
                    self._input.append(info)
                else:
                    raise EOFError
        except EOFError:
            pass

    def _get_redirect_input(self):
        for line in sys.stdin.readlines():
            data = line.strip()
            if data:
                info = self._unformat_spec.parse(data)
                self._input.append(info)
            else:
                continue

    def _get_file_input(self):
        with open(self._args.input, "r") as f:
            for line in f.readlines():
                data = line.strip()
                if data:
                    info = self._unformat_spec.parse(data)
                    self._input.append(info)
                else:
                    continue

    def _get_args_input(self):
        info = self._unformat_spec.parse(self._args.input.strip())
        self._input.append(info)

    def _validate_format(self):
        # interpret escape sequences
        try:
            self._args.format = bytes(self._args.format,
                                      API.ENCODING).decode(API.DECODING)
        except TypeError:
            self._args.format = self._args.format.decode(API.DECODING)

        info = dict((key, None) for key in API.INFO_KEYS)

        try:
            self._args.format.format(**info)
        except KeyError:
            print("Invalid Format Specifier !")
            sys.exit(1)
        else:
            self._format_spec = self._args.format + "\n"
            self._unformat_spec = parse.compile(self._args.format)

    def _get(self):
        # create request payload
        payload = {
            "state": self._args.state,
            "sort": self._args.sort,
            "detailType": "complete",
            "total": "1",            
        }
        if self._args.content != "all":
            payload["contentType"] = self._args.content

        if self._args.query:
            payload["search"] = self._args.query

        if self._args.tag == "-1":
            pass
        elif self._args.tag == "0":
            payload["tag"] = "_untagged_"
        else:
            payload["tag"] = self._args.tag

        if self._args.favorite != -1:
            payload["favorite"] = self._args.favorite

        if self._args.domain:
            payload["domain"] = self._args.domain

        if self._args.since:
            payload["since"] = datetime.strptime(self._args.since,
                                                 "%Y-%m-%d").timestamp()

        self._payload = payload
        self._api_endpoint = API.RETRIEVE_URL

        # Set up pagination controls
        offset = 0
        count = self._args.count if self._args.count != -1 else None
        page_limit = 30  # API returns a maximum of 30 items per request
        all_items = []

        while True:
            # Adjust count for each request: request either page_limit or remaining items
            current_count = min(page_limit, count - len(all_items)) if count else page_limit
            payload["count"] = current_count
            payload["offset"] = offset

            # Make the API request
            self._payload = payload
            self._api_request()

            # Extract items from response
            items = self._response.data.get("list", {})
            
            if len(items) == 0:
                # No items on this page, exit loop if empty
                break

            # Process and add current page of items to all_items
            all_items.extend([{
                "id": item.get("item_id"),
                "title": item.get("resolved_title"),
                "link": item.get("resolved_url"),
                "excerpt": item.get("excerpt"),
                "tags": self._process_tags(item.get("tags")),
                "time_added": item.get("time_added"),
                "time_updated": item.get("time_updated"),
                "domain": item.get("domain_metadata", {}).get("name"),
            } for item in items.values()])

            # Check if enough items have been retrieved
            if count and len(all_items) >= count:
                all_items = all_items[:count]  # Trim to requested count
                break

            # Check if there are more pages available (pagination condition)
            total = int(self._response.data.get("total", 0))
            if offset + current_count >= total:
                break

            # Update offset for next request
            offset += current_count

        # Final output collection
        self._output = tuple(all_items)

        if not all_items:
            print("No items found!")
            sys.exit(0)

    def _process_tags(self, tags):
        if tags:
            return list(tags.keys())

    def _put(self):
        payload = {
            "actions":
            tuple({
                "action": "add",
                "url": info["link"],
            } for info in self._input)
        }

        self._payload = payload
        self._api_endpoint = API.MODIFY_URL

        self._api_request()

    def _modify(self):
        if self._args.delete:
            action = "delete"
        elif self._args.archive != -1:
            if self._args.archive == 1:
                action = "archive"
            else:
                action = "readd"  # i.e. re-add
        elif self._args.favorite != -1:
            if self._args.favorite == 1:
                action = "favorite"
            else:
                action = "unfavorite"
        else:
            action = ""

        payload = {
            "actions":
            tuple({
                "action": action,
                "item_id": info["id"],
            } for info in self._input),
        }

        self._payload = payload
        self._api_endpoint = API.MODIFY_URL

        self._api_request()

    def run(self):

        # validate format specifier
        self._validate_format()

        if self._args.do == "get":
            self._get()

            for info in self._output:
                self._print_to_console(info)
                if self._args.archive:
                    self._save_to_archive(info)
                elif self._args.output == "browser":
                    self._open_in_browser(info)
            else:
                if self._args.output:
                    self._output_to_file()

        else:
            if self._args.input == "console":
                self._get_console_input()
            elif self._args.input == "redirect":
                self._get_redirect_input()
            elif self._args.input.startswith("http"):
                self._get_args_input()
            else:
                self._get_file_input()

            if self._args.do == "put":
                self._put()
            elif self._args.do == "mod":
                self._modify()
