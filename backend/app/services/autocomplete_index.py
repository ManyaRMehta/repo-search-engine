from dataclasses import dataclass, field
from platform import node
from sys import prefix

from matplotlib.pylab import character


@dataclass
class TrieNode:
    children: dict[str, "TrieNode"] = field(default_factory=dict)
    is_terminal: bool = False
    terminal_term: str | None = None


class AutocompleteIndex:
    def __init__(self) -> None:
        self.root = TrieNode()

    def insert(self, term: str) -> None:
        normalized_term = term.lower()

        current_node = self.root

        for character in normalized_term:
            if character not in current_node.children:
                current_node.children[character] = TrieNode()

            current_node = current_node.children[character]

        current_node.is_terminal = True

        if (
            current_node.terminal_term is None
            or (
                current_node.terminal_term == current_node.terminal_term.lower()
                and term != term.lower()
            )
        ):
            current_node.terminal_term = term

    def build(self, terms: set[str]) -> None:
        for term in terms:
            self.insert(term)

    def suggest(self, prefix: str, limit: int = 10) -> list[str]:
        normalized_prefix = prefix.lower()
        current_node = self.root

        for character in normalized_prefix:
            if character not in current_node.children:
                return []

            current_node = current_node.children[character]

        suggestions: list[str] = []

        def collect_terms(node: TrieNode, current_term: str) -> None:
            if len(suggestions) >= limit:
                return

            if node.is_terminal and node.terminal_term is not None:
                suggestions.append(node.terminal_term)

            for character in sorted(node.children):
                collect_terms(
                    node.children[character],
                    current_term + character,
                )

        collect_terms(current_node, normalized_prefix)

        return suggestions