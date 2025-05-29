"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from typing import Any, Protocol, TypedDict

from graphiti_core.prompts.models import Message, PromptFunction
from graphiti_core.prompts.prompt_helpers import DO_NOT_ESCAPE_UNICODE

from .invalidate_nodes import Prompt as InvalidateNodesPrompt
from .invalidate_nodes import Versions as InvalidateNodesVersions
from .invalidate_nodes import versions as invalidate_nodes_versions


class ExtendedPromptLibrary(Protocol):
    invalidate_nodes: InvalidateNodesPrompt


class ExtendedPromptLibraryImpl(TypedDict):
    invalidate_nodes: InvalidateNodesVersions


class VersionWrapper:
    def __init__(self, func: PromptFunction):
        self.func = func

    def __call__(self, context: dict[str, Any]) -> list[Message]:
        messages = self.func(context)
        for message in messages:
            message.content += DO_NOT_ESCAPE_UNICODE if message.role == 'system' else ''
        return messages


class PromptTypeWrapper:
    def __init__(self, versions: dict[str, PromptFunction]):
        for version, func in versions.items():
            setattr(self, version, VersionWrapper(func))


class ExtendedPromptLibraryWrapper:
    def __init__(self, library: ExtendedPromptLibraryImpl):
        for prompt_type, versions in library.items():
            setattr(self, prompt_type, PromptTypeWrapper(versions))  # type: ignore[arg-type]


EXTENDED_PROMPT_LIBRARY_IMPL: ExtendedPromptLibraryImpl = {
    'invalidate_nodes': invalidate_nodes_versions,
}

prompt_library: ExtendedPromptLibrary = ExtendedPromptLibraryWrapper(EXTENDED_PROMPT_LIBRARY_IMPL)  # type: ignore[assignment] 