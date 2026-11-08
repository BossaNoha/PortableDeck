"""Table placement and position calculations for the Game model."""

class TablePlacementActions:
    def initialize_table_limits(self, enabled=False, rows=3, columns=5):
        if any(not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 20 for value in (rows, columns)):
            raise ValueError("Maximum table rows and columns must be between 1 and 20.")
        self.enable_table_limits = bool(enabled)
        self.max_table_rows, self.max_table_columns = rows, columns

    def within_table_limits(self, position):
        return not self.enable_table_limits or (0 <= position[0] < self.max_table_rows and 0 <= position[1] < self.max_table_columns)


    def play_to_table(self, index, position=None, face_up=True):
        if not self.enable_table:
            return None
        if not face_up and not self.allow_face_down_table_cards:
            return None
        if self.allow_play_in_front_of_players:
            if position is None:
                position = self.default_table_position()
            if (
                not isinstance(position, (tuple, list))
                or len(position) != 2
                or any(not isinstance(value, int) or isinstance(value, bool) for value in position)
                or tuple(position) not in self.available_table_positions()
            ):
                return None
            position = list(position)
        elif self.allow_positioned_play:
            if position is None:
                position = self.default_table_position()
            if (
                not isinstance(position, (tuple, list))
                or len(position) != 2
                or any(not isinstance(value, int) or isinstance(value, bool) for value in position)
                or tuple(position) not in self.available_table_positions()
            ):
                return None
            position = list(position)
        elif self.allow_move_cards_on_table:
            position = list(self.default_table_position())
        else:
            position = None
        player = self.players[self.current_player_index]
        card = player.play_card(index)
        if card:
            entry = {"player": player.name, "card": card, "face_up": bool(face_up)}
            if self.allow_positioned_play or self.allow_move_cards_on_table or self.allow_play_in_front_of_players:
                entry["position"] = position
            self.table_cards.append(entry)
            self.log_action(player.name, "play", card)
            return card
        return None

    def available_table_positions(self):
        occupied = {
            tuple(entry["position"])
            for entry in self.table_cards
            if isinstance(entry.get("position"), (tuple, list)) and len(entry["position"]) == 2
        }
        if self.enable_table_limits:
            return {(row, column) for row in range(self.max_table_rows)
                    for column in range(self.max_table_columns)
                    if (row, column) not in occupied and (not self.allow_play_in_front_of_players or row < len(self.players))}
        if not occupied:
            if self.allow_play_in_front_of_players:
                return {(index, 0) for index in range(len(self.players))}
            return {(0, 0)}
        if self.allow_play_in_front_of_players:
            positions = set()
            for player_index in range(len(self.players)):
                columns = [column for row, column in occupied if row == player_index]
                positions.add((player_index, max(columns) + 1 if columns else 0))
            return positions
        available = set()
        for row, column in occupied:
            for neighbor in (
                (row - 1, column),
                (row + 1, column),
                (row, column - 1),
                (row, column + 1),
            ):
                if neighbor not in occupied:
                    available.add(neighbor)
        # Keep the original horizontal line compact and expose just one
        # continuation slot at its right edge. Vertical rows still get the
        # adjacent slots needed for spatial play.
        main_line_columns = [column for row, column in occupied if row == 0]
        if main_line_columns:
            next_column = max(main_line_columns) + 1
            available = {spot for spot in available if spot[0] != 0}
            if (0, next_column) not in occupied:
                available.add((0, next_column))
        else:
            available = {spot for spot in available if spot[0] != 0}
            available.add((0, 0))
        return available

    def _compact_main_line(self):
        """Close gaps between cards in the original row after a removal."""
        if self.enable_table_limits or self.allow_face_down_table_cards or self.allow_move_table_sequences:
            return
        if self.allow_play_in_front_of_players:
            for player_index in range(len(self.players)):
                lane = sorted(
                    (entry for entry in self.table_cards
                     if isinstance(entry.get("position"), (tuple, list))
                     and len(entry["position"]) == 2
                     and entry["position"][0] == player_index),
                    key=lambda entry: entry["position"][1],
                )
                for column, entry in enumerate(lane):
                    entry["position"] = [player_index, column]
            return
        main_line = sorted(
            (entry for entry in self.table_cards
             if isinstance(entry.get("position"), (tuple, list))
             and len(entry["position"]) == 2
             and entry["position"][0] == 0),
            key=lambda entry: entry["position"][1],
        )
        for column, entry in enumerate(main_line):
            entry["position"] = [0, column]

    def move_table_card(self, table_index, position):
        """Move a selected table card into an available table position."""
        if (
            not self.allow_move_cards_on_table
            or not 0 <= table_index < len(self.table_cards)
            or not isinstance(position, (tuple, list))
            or len(position) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) for value in position)
            or tuple(position) not in self.available_table_positions()
        ):
            return None
        entry = self.table_cards[table_index]
        if self.allow_move_table_sequences:
            source = entry.get("position")
            if not isinstance(source, (tuple, list)) or len(source) != 2:
                return None
            source_row, source_column = source
            target_row, target_column = position
            if source_column == target_column:
                return None
            sequence = sorted(
                (
                    card for card in self.table_cards
                    if isinstance(card.get("position"), (tuple, list))
                    and len(card["position"]) == 2
                    and card["position"][1] == source_column
                    and card["position"][0] >= source_row
                ),
                key=lambda card: card["position"][0],
            )
            if not sequence or any(not card.get("face_up", True) for card in sequence):
                return None
            moving = {id(card) for card in sequence}
            occupied = {
                tuple(card["position"]) for card in self.table_cards if id(card) not in moving
            }
            targets = [(target_row + offset, target_column) for offset in range(len(sequence))]
            if any(target in occupied or not self.within_table_limits(target) for target in targets):
                return None
            for card, target in zip(sequence, targets):
                card["position"] = list(target)
            remaining = [
                card for card in self.table_cards
                if card.get("position", [None, None])[1] == source_column
                and not card.get("face_up", True)
            ]
            if remaining:
                newly_exposed = max(remaining, key=lambda card: card["position"][0])
                newly_exposed["face_up"] = True
            self.log_action(entry["player"], "move_table_sequence", entry["card"])
            return [card["card"] for card in sequence]

        entry["position"] = list(position)
        self._compact_main_line()
        self.log_action(entry["player"], "move_table_card", entry["card"])
        return entry["card"]

    def default_table_position(self):
        if self.enable_table_limits:
            available = self.available_table_positions()
            if self.allow_play_in_front_of_players:
                available = {spot for spot in available if spot[0] == self.current_player_index}
            return min(available) if available else None
        if self.allow_play_in_front_of_players:
            player_index = self.current_player_index
            columns = [
                entry["position"][1]
                for entry in self.table_cards
                if isinstance(entry.get("position"), (tuple, list))
                and len(entry["position"]) == 2
                and entry["position"][0] == player_index
            ]
            return player_index, max(columns) + 1 if columns else 0
        if not self.table_cards:
            return 0, 0
        main_row_columns = [
            entry["position"][1]
            for entry in self.table_cards
            if isinstance(entry.get("position"), (tuple, list))
            and len(entry["position"]) == 2
            and entry["position"][0] == 0
        ]
        if main_row_columns:
            candidate = (0, max(main_row_columns) + 1)
            if candidate in self.available_table_positions():
                return candidate
        return min(self.available_table_positions())

