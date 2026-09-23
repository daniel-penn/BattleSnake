from api import *

DIRECTIONS = {"U": (0, 1), "D": (0, -1), "L": (-1, 0), "R": (1, 0)}
CLAUSTROPHOBIA = 6


class MyBot(CodeBattlesBot):
    def _escape_space(self, start, occupied_tiles):
        """Count reachable tiles with bodies and radius-two head crosses blocked."""
        blocked_tiles = set(occupied_tiles)
        myself = self.context.get_myself()
        my_head = self.context.get_position(myself)[-1]
        my_length = self.context.get_length(myself)
        head_x, head_y = my_head
        bodies = [
            self.context.get_position(player)
            for player in self.context.get_active_players()
        ]
        for body in bodies:
            blocked_tiles.difference_update(body)
        for body in bodies:
            # Bodies run tail-first such that segment n clears after n+1 moves.
            for tail_index, (tile_x, tile_y) in enumerate(body):
                distance = abs(tile_x - head_x) + abs(tile_y - head_y)
                if tail_index > 0 and distance <= tail_index:
                    blocked_tiles.add((tile_x, tile_y))
        threatening_heads = []
        for player in self.context.get_active_players():
            opponent_x, opponent_y = self.context.get_position(player)[-1]
            if (
                (opponent_x, opponent_y) == my_head
                or self.context.get_length(player) < my_length
            ):
                continue
            threatening_heads.append((opponent_x, opponent_y))

        board_width, board_height = self.context.get_game_size()
        for tile_x in range(board_width):
            for tile_y in range(board_height):
                distance = abs(tile_x - head_x) + abs(tile_y - head_y)
                # Each step expands the opponent's reachable area by one tile
                if any(
                    abs(tile_x - opponent_x) + abs(tile_y - opponent_y) <= distance
                    for opponent_x, opponent_y in threatening_heads
                ):
                    blocked_tiles.add((tile_x, tile_y))

        if not self.context.in_bounds(start) or start in blocked_tiles:
            return 0

        visited = {start}
        pending = [start]
        while pending:
            tile_x, tile_y = pending.pop()
            for offset_x, offset_y in DIRECTIONS.values():
                neighbor = (tile_x + offset_x, tile_y + offset_y)
                if not self.context.in_bounds(neighbor) or neighbor in blocked_tiles:
                    continue
                if neighbor not in visited:
                    visited.add(neighbor)
                    pending.append(neighbor)

        return len(visited)

    def _should_seek_apple(self, apple):
        """
        Head towards an apple if it's one turn away and nobody can beat us to it.
        """
        my_body = self.context.get_position(self.context.get_myself())
        head_x, head_y = my_body[-1]
        apple_x, apple_y = apple
        if head_x != apple_x and head_y != apple_y:
            return False
        distance_to_apple = abs(head_x - apple_x) + abs(head_y - apple_y)
        if distance_to_apple == 0:
            return False

        # For each player, check if they're closer to the apple than us.
        for player in self.context.get_active_players():
            player_body = self.context.get_position(player)
            if player_body == my_body:
                continue
            opponent_x, opponent_y = player_body[-1]
            opponent_distance = abs(opponent_x - apple_x) + abs(opponent_y - apple_y)
            if opponent_distance <= distance_to_apple:
                return False
        return True

    def _score_side(self, direction):
        """
        Calculate our preference for a side of the board.
        """
        my_body = self.context.get_position(self.context.get_myself())
        head_x, head_y = my_body[-1]
        my_tiles = set(my_body)
        occupied_tiles = set(self.context.get_occupied_tiles())
        opposing_heads = {
            self.context.get_position(player)[-1]
            for player in self.context.get_active_players()
        } - {my_body[-1]}
        apple_tiles = set(self.context.get_apples())
        board_width, board_height = self.context.get_game_size()
        offset_x, offset_y = DIRECTIONS[direction]

        # Calculate score
        side_score = 0
        for tile_x in range(board_width):
            for tile_y in range(board_height):
                # Only count tiles on the chosen direction's side of the line through our head.
                if (tile_x - head_x) * offset_x + (tile_y - head_y) * offset_y > 0:
                    tile = (tile_x, tile_y)
                    side_score += (
                        -1
                        if tile in my_tiles  # Tile belongs to us
                        else -6
                        if tile in opposing_heads  # Opposing head :(
                        else 0
                        if tile in occupied_tiles  # Opposing body
                        else 2
                        if tile in apple_tiles  # Tile is apple
                        else 1  # Tile is empty
                    )
        return side_score

    def setup(self):
        self.direction = "U"

    def run(self):
        # Get relevant vars from context
        myself = self.context.get_myself()
        my_body = self.context.get_position(myself)
        head_x, head_y = my_body[-1]
        occupied_tiles = set(self.context.get_occupied_tiles())
        apple_coords = self.context.get_apples()
        my_length = self.context.get_length(myself)
        opposing_heads = {
            self.context.get_position(player)[-1]
            for player in self.context.get_active_players()
            if self.context.get_length(player) >= my_length
        } - {my_body[-1]}
        threatened_tiles = {
            (opponent_x + offset_x, opponent_y + offset_y)
            for opponent_x, opponent_y in opposing_heads
            for offset_x, offset_y in DIRECTIONS.values()
        }

        # Read our heading from the body
        if len(my_body) > 1:
            heading = (head_x - my_body[-2][0], head_y - my_body[-2][1])
            for direction, offset in DIRECTIONS.items():
                if offset == heading:
                    self.direction = direction
        forward_x, forward_y = DIRECTIONS[self.direction]

        # 1. Avoid walls, bodies, equal/longer head threats, and reversing.
        safe_directions = []
        for direction, (offset_x, offset_y) in DIRECTIONS.items():
            tile = (head_x + offset_x, head_y + offset_y)
            if (
                (offset_x, offset_y) != (-forward_x, -forward_y)
                and self.context.in_bounds(tile)
                and tile not in occupied_tiles
                and tile not in threatened_tiles
            ):
                safe_directions.append(direction)

        # Reject regions with CLAUSTROPHOBIA or fewer tiles
        escape_spaces = {}
        escape_directions = []
        for direction in safe_directions:
            offset_x, offset_y = DIRECTIONS[direction]
            tile = (head_x + offset_x, head_y + offset_y)
            space = self._escape_space(tile, occupied_tiles)
            escape_spaces[direction] = space
            if space > CLAUSTROPHOBIA:
                escape_directions.append(direction)

        if escape_directions:
            safe_directions = escape_directions
        elif safe_directions:
            # If every option is cramped, choose the one with most room
            self.direction = max(
                safe_directions,
                key=lambda direction: (
                    escape_spaces[direction],
                    self._score_side(direction),
                ),
            )
            self.context.set_direction(self.direction)
            return

        # 2. Head towards an apple if one is available.
        for apple in apple_coords:
            if not self._should_seek_apple(apple):
                continue
            apple_x, apple_y = apple
            if apple_x == head_x:
                direction = "U" if apple_y > head_y else "D"
            else:
                direction = "R" if apple_x > head_x else "L"
            if direction in safe_directions:
                self.direction = direction
                self.context.set_direction(direction)
                return

        # 3. If straight is blocked, score the two sides of our heading.
        if safe_directions and self.direction not in safe_directions:
            self.direction = max(safe_directions, key=self._score_side)

        self.context.set_direction(self.direction)
