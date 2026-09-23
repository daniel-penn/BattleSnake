from api import *

DIRECTIONS = {"U": (0, 1), "D": (0, -1), "L": (-1, 0), "R": (1, 0)}


class MyBot(CodeBattlesBot):
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
                        -1 if tile in my_tiles # Tile belongs to us
                        else -6 if tile in opposing_heads # Opposing head :(
                        else 0 if tile in occupied_tiles # Opposing body
                        else 2 if tile in apple_tiles # Tile is apple
                        else 1 # Tile is empty
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
        opposing_heads = {
            self.context.get_position(player)[-1]
            for player in self.context.get_active_players()
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

        # 1. Avoid walls, snakes, tiles next to opposing heads, and reversing.
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
