"""
A small, dependency-free DOM for the hardHats accessibility checks.

Standard-library html.parser only (nothing is pip-installed into his env). The
checks need to ask real structural questions - every img, heading levels in
order, form controls and their labels, interactive elements, duplicate ids - so
they query this tree instead of guessing with regex.
"""
from __future__ import annotations

from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
INTERACTIVE = {"a", "button", "input", "select", "textarea", "details", "summary"}


class Node:
    __slots__ = ("tag", "attrs", "parent", "children", "text", "line")

    def __init__(self, tag, attrs=None, line=0):
        self.tag = tag
        self.attrs = attrs or {}
        self.parent = None
        self.children: list[Node] = []
        self.text = ""
        self.line = line

    def get(self, name, default=None):
        return self.attrs.get(name, default)

    def has(self, name):
        return name in self.attrs

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def find(self, *tags):
        tset = set(tags)
        return [n for n in self.walk() if n.tag in tset]

    def inner_text(self):
        out = [self.text]
        for c in self.children:
            out.append(c.inner_text())
        return " ".join(t for t in out if t).strip()

    def role(self):
        return (self.get("role") or "").strip().lower()

    def is_interactive(self):
        if self.tag in INTERACTIVE and not (self.tag == "a" and not self.has("href")):
            return True
        if self.role() in {"button", "link", "checkbox", "menuitem", "tab", "switch"}:
            return True
        return self.has("onclick") or self.has("tabindex")


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.getpos()[0])
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.getpos()[0])
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].text = (self.stack[-1].text + " " + data.strip()).strip()


def parse(html: str) -> Node:
    b = _Builder()
    b.feed(html)
    return b.root
