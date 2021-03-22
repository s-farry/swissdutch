import math
import itertools
import operator
from copy import copy
from swissdutch.constants import FloatStatus, Colour, ColourPref

class ScoreBracket:
    def __init__(self, score, players):
        self._score                   = score
        self._all_players             = list(players)
        self._remaining_players       = None
        self._criteria                = PairingCriteria(self)
        self._pairings                = []
        self._bye                     = None
        self._transpositions          = None
        self._exchanges               = None
        self._exchange_length         = 1
        self._saved_transpositions    = None
        self._incompatible_player     = None
        self._paired_floaters         = False
        self._force_homogenous        = False

    @property
    def all_players(self):
        return self._all_players

    @property
    def x(self):
        return self._x

    @property
    def p(self):
        return self._p

    @property
    def z(self):
        return self._z
    
    @property
    def odd_round(self):
        return self._context.round_no % 2

    @property
    def last_round(self):
        return self._context.last_round

    @property
    def round_no(self):
        return self._context.round_no

    def generate_pairings(self, ctx):
        self._context = ctx
        step = self._c1()
        while step:
            step = step()

    def finalize_pairings(self):
        for pair in self._pairings:
            self._assign_colours(pair)

        if self._bye:
            p = self._bye
            p.bye(self._context.bye_value)

    def add_player(self, player):
        self._all_players.append(player)

    def remove_player(self, player):
        self._all_players.remove(player)

    def can_backtrack(self, player):
        return player != self._incompatible_player

    def backtrack(self, player):
        self._reset()
        self._all_players.append(player)

    @property
    def _lsb(self):
        return self._context.lowest_score_bracket

    @property
    def _players(self):
        return self._remaining_players if self._remaining_players else self._all_players

    @property
    def _heterogenous(self):
        if self._force_homogenous : return False
        return (any(p.score > self._score for p in self._players)
                and sum(p.score > self._score for p in self._players) / len(self._players) < 0.5)

    @property
    def _majority_expected_colour(self):
        white = sum(p.expected_colour == Colour.white for p in self._players)
        black = sum(p.expected_colour == Colour.black for p in self._players)
        
        col = Colour.none
        
        if white > black:
            col = Colour.white
        elif black > white:
            col = Colour.black

        return col

    @property
    def _p0(self):
        return math.floor(len(self._players)/2)

    @property
    def _m0(self):
        return sum(p.score > self._score for p in self._players)
    
    def _get_transpositions(self):
        # get a list of transpositions but only care about the order of the first
        # elements corresponds to s1 for efficiency
        permutations_sub = itertools.permutations(self._s2, len(self._s1))
        permutations = [ list(perms) + [ p  for p in self._s2 if p not in perms] for perms in permutations_sub  ]
        return iter(permutations)



    def _reset(self):
        self._remaining_players       = None
        self._pairings                = []
        self._bye                     = None
        self._exchanges               = None
        self._exchange_length         = 1
        self._incompatible_player     = None

    def _calculate_x1(self):
        white   = sum(p.expected_colour == Colour.white for p in self._players)
        black   = sum(p.expected_colour == Colour.black for p in self._players)
        neither = len(self._players) - white - black

        if white < black:
            white += neither
        else:
            black += neither

        return math.floor(abs((white - black) / 2))

    def _calculate_z1(self):
        if self.odd_round:
            return self._x1 # only calculate z1 in even rounds

        maj_col = self._majority_expected_colour
        num_var = sum(p.colour_preference == ColourPref.mild 
                      and p.expected_colour == maj_col 
                      for p in self._players)
        return max(0,self._x1 - num_var)

    def _assign_colours(self, pair):
        p1, p2 = pair
        if abs(p1.colour_preference) > abs(p2.colour_preference):
            p1.pair_both(p2, p1.expected_colour)
        elif abs(p1.colour_preference) < abs(p2.colour_preference):
            p2.pair_both(p1, p2.expected_colour)
        elif p1.score > p2.score:
            p1.pair_both(p2, p1.expected_colour)
        elif p1.score < p2.score:
            p2.pair_both(p1, p2.expected_colour)
        elif p1.pairing_no < p2.pairing_no:
            p1.pair_both(p2, p1.expected_colour)
        else:
            p2.pair_both(p1, p2.expected_colour)

    def _c1(self):
        print('c1')
        # c2a
        self._p1 = self._p0
        self._m1 = self._m0
        # c2b
        self._x1 = self._calculate_x1()
        self._z1 = self._calculate_z1()

        step = self._c2a

        for p1 in self._players:
            compatible = False

            other_players = copy(self._players)
            other_players.remove(p1)

            for p2 in other_players:
                if self._criteria.b1a(p1, p2) and self._criteria.b2(p1, p2):
                    compatible = True
                    break

            if not compatible:
                player = p1
                if len(other_players) == 1:
                    player = p1 if p1.score >= p2.score else p2

                self._incompatible_player = player

                if player.score > self._score:
                    step = self._c13 if self._lsb else self._c12
                    break
                elif self._lsb:
                    step = self._c13
                    break
                elif self._context.can_downfloat(player):
                    self._context.downfloat(player)

        if not len(self._players):
            step = None

        return step

    def _c2a(self):
        self._p1 = self._p0
        self._m1 = self._m0
        return self._c2b

    def _c2b(self):
        self._x1 = self._calculate_x1()
        self._z1 = self._calculate_z1()
        return self._c3a

    def _c3a(self):
        self._p = self._m1 if self._heterogenous else self._p1
        return self._c3b

    def _c3b(self):
        self._criteria.b2_enabled_for_top_scorers = True
        return self._c3c

    def _c3c(self):
        self._criteria.a7d_enabled = True
        return self._c3d

    def _c3d(self):
        self._x = self._x1
        self._z = self._z1
        return self._c3e

    def _c3e(self):
        self._criteria.b5_enabled_for_downfloaters = True
        return self._c3f

    def _c3f(self):
        self._criteria.b6_enabled_for_downfloaters = True
        return self._c3g

    def _c3g(self):
        self._criteria.b5_enabled_for_upfloaters = True
        return self._c3h

    def _c3h(self):
        self._criteria.b6_enabled_for_upfloaters = True
        return self._c4

    def _c4(self):
        #print('c4: p, p1, m1, z, z1',self._p,self._p1,self._m1, self._z, self._z1)
        if self._z < 0 or self._z1 < 0 : raise Exception('values should not be less than 0')
        self._players.sort(key=operator.attrgetter('pairing_no'))
        self._players.sort(key=operator.attrgetter('score'), reverse=True)

        self._s1 = self._players[:self._p]
        self._s2 = self._players[self._p:]

        return self._c5

    def _c5(self):
        self._s1.sort(key=operator.attrgetter('pairing_no'))
        self._s1.sort(key=operator.attrgetter('score'), reverse=True)

        self._s2.sort(key=operator.attrgetter('pairing_no'))
        self._s2.sort(key=operator.attrgetter('score'), reverse=True)

        return self._c6

    def _c6(self):
        #print('c6',self._p,self._p1,self._m1, len(self._s1), len(self._s2))
        #print('s1 in c6',len(self._s1),[(s.name,s.score) for s in self._s1])
        #print('s2 in c6',len(self._s2),[(s.name,s.score) for s in self._s2])
        if len(self._s2) < len(self._s1):
            raise Exception('this should not be happening', [(s.name,s.score) for s in self._s2], [(s.name,s.score) for s in self._s1])
        pairings = [(self._s1[i], self._s2[i]) for i in range(len(self._s1))]
        #print('pairings: ', [(p[0].name, p[0].pairing_no, p[1].name, p[1].pairing_no) for p in pairings])
        unpaired = list(set(self._s1 + self._s2) - set(sum(pairings, ())))
        bye      = unpaired[0] if len(unpaired) == 1 and self._lsb else None
        floater  = unpaired[0] if not(bye) and len(unpaired) == 1 else None

        step = None
        if self._criteria.satisfied(pairings, floater, bye):
            if floater:
                def alt_floaters(): 
                    return sum(self._criteria.b5(p) 
                               and self._criteria.b6(p) 
                               and self._context.can_downfloat(p)
                               for p in self._players)

                if self._context.can_downfloat(floater) or not alt_floaters():
                    # If the player isn't allowed to float and there are no 
                    # alternative floaters then we force him to float anyway 
                    # and let the next bracket figure out what to do with him.
                    self._pairings += pairings
                    self._context.downfloat(floater)
                else:
                    step = self._c7 # try to find a different floater
            else:
                self._pairings += pairings
                self._bye       = bye

                if len(unpaired) > 1:
                    # Pair remainder
                    self._paired_floaters      = True
                    self._saved_transpositions = self._transpositions
                    self._saved_p              = self._p
                    self._transpositions       = None
                    self._exchanges            = None
                    self._remaining_players    = unpaired
                    self._p                    = self._p1 - self._m1 if self._heterogenous else math.floor(len(self._remaining_players)/2.0)
                    if self._p < 0 : raise Exception('self._pt is less than 0')
                    #self._x                    = self._x1
                    step                       = self._c4
        else:
            step = self._c7

        return step

    def _c7(self):
        #print('c7')
        if not self._transpositions:
            #self._transpositions = itertools.permutations(self._s2)
            self._transpositions = self._get_transpositions()
            next(self._transpositions) # skip 1st one since it's equal to current self._s2
        step = self._c6

        try:
            self._s2 = list(next(self._transpositions))
        except StopIteration: # no more transpositions
            self._transpositions = None
            step = self._c10a if self._heterogenous else self._c8

        return step

    @staticmethod
    def _generate_exchanges(s1, s2, n):
        s1_subsets = sorted(itertools.combinations(s1, r=n),
                            key=lambda players: sum(p.pairing_no for p in players),
                            reverse=True)
        s1_subsets.sort(key=lambda players: sum(p.score for p in players), 
                        reverse=True)
        s2_subsets = sorted(itertools.combinations(s2, r=n),
                            key=lambda players: sum(p.pairing_no for p in players))
        s2_subsets.sort(key=lambda players: sum(p.score for p in players))
        end_s1_subsets = len(s1_subsets) - 1
        end_s2_subsets = len(s2_subsets) - 1

        def diff(s1sub, s2sub): 
            return abs(sum(p.score for p in s1sub) - sum(p.score for p in s2sub))

        exchanges = []
        if not(s1_subsets) or not(s2_subsets):
            return exchanges

        min_diff = diff(s1_subsets[0], s2_subsets[0])
        max_diff = diff(s1_subsets[-1], s2_subsets[-1])

        delta = min_diff
        i = 0
        k = 0

        while delta <= max_diff:
            if delta == diff(s1_subsets[i], s2_subsets[k]):
                s1_exchange = copy(s1)
                s2_exchange = copy(s2)

                for player in s1_subsets[i]:
                    s1_exchange.remove(player)
                    s2_exchange.append(player)
                for player in s2_subsets[k]:
                    s2_exchange.remove(player)
                    s1_exchange.append(player)
                exchanges.append( ( s1_exchange, s2_exchange ) )
            if k < end_s2_subsets:
                k += 1
                continue
            if i < end_s1_subsets:
                i += 1
                k = 0
                continue
            delta += 1
            i = 0
            k = 0

        return exchanges

    def _c8(self):
        step = self._c5

        if self._exchanges == None:
            self._s1.sort(key=operator.attrgetter('pairing_no'), reverse=True)
            self._s1.sort(key=operator.attrgetter('score'))

            self._s2.sort(key=operator.attrgetter('pairing_no'))
            self._s2.sort(key=operator.attrgetter('score'), reverse=True)

            self._exchanges = self._generate_exchanges(self._s1, self._s2,
                                                       self._exchange_length)

        exchange = None
        try:
            exchange = self._exchanges.pop(0)
        except IndexError: # no more exchanges (for this subset size)
            self._exchanges = None
            self._exchange_length += 1

            if self._exchange_length > self._p:
                self._exchange_length = 1
                self._remaining_players = None
                step = self._c9 if self._heterogenous else self._c10a
            else:
                step = self._c8 # generate another set of exchanges
        else:
            
            self._s1, self._s2 = exchange

        return step

    def _c9(self):
        print("running c9")
        self._pairings       = []
        self._transpositions = self._saved_transpositions
        self._p              = self._saved_p
        #self._x              = self._x1
        self._s1             = self._players[:self._p]
        self._s2             = self._players[self._p:]
        self._remaining_players = None
        self._exchanges      = None
        self._exchange_length = 1
        return self._c7

    def _c10a(self):
        #print("running c10a")
        step = self._c4
        if not self._criteria.b6_enabled_for_upfloaters:
            step = self._c10b
        self._criteria.b6_enabled_for_upfloaters = False
        return step

    def _c10b(self):
        #print("running c10b")
        step = self._c3h
        if not self._criteria.b5_enabled_for_upfloaters:
            step = self._c10c
        self._criteria.b5_enabled_for_upfloaters = False
        return step

    def _c10c(self):
        #print("running c10c")
        step = self._c3g
        if not self._criteria.b6_enabled_for_downfloaters:
            step = self._c10d
        self._criteria.b6_enabled_for_downfloaters = False
        return step

    def _c10d(self):
        #print("running c10d")
        step = self._c3f
        if not self._criteria.b5_enabled_for_downfloaters:
            step = self._c10e
        self._criteria.b5_enabled_for_downfloaters = False
        return step

    def _c10e(self):
        print("running c10e, x, p1, z, z1", self._x, self._p1, self._z, self._z1)
        step = self._c3e
        if self.odd_round:
            if self._x < self._p1:
                self._x += 1
            else:
                step = self._c14a if not self._heterogenous else self._c14b
        else:
            if self._z < self._x:
                self._z += 1
            elif self._z == self._x and self._x < self._p1:
                self._x += 1
                self._z = self._z1
            else:
                step = self._c14a if not self._heterogenous else self._c14b

        return step

    def _c10f(self):
        #print("running c10f")
        if self.odd_round:
            self._criteria.a7d_enabled = False
        return self._c3d

    def _c10g(self):
        print("running c10g")
        if self.last_round:
            self._criteria.b2_enabled_for_top_scorers = False
        return self._c3c

    def _c12(self):
        print("running c12")
        step = None
        
        player = self._incompatible_player
        if self._context.can_backtrack(player):
            self._context.backtrack(player)
            self._incompatible_player = None
        elif self._heterogenous:
            step = self._c14b
        else:
            step = self._c14a

        return step

    def _c13(self):
        print("running c13")
        step = None

        if self._heterogenous:
            step = self._c14b
        else:
            player = self._incompatible_player
            if self._context.can_backtrack(player):
                self._context.backtrack(player)
                self._incompatible_player = None
            else:
                collapsed = self._context.collapse_previous_score_bracket()
                self._incompatible_player = None
                if not collapsed:
                    step = self._pairing_error
                else:
                    step = self._c1

        return step

    def _c14a(self):
        print("running c14a")
        step = self._c3a
        if self._p1 == 0:
            if not self._lsb:
                collapsed = self._context.collapse_current_score_bracket()
                if not collapsed : step = self._pairing_error
                else: step = None
            else:
                self._reset()
                collapsed = self._context.collapse_previous_score_bracket()
                if not collapsed: step = self._pairing_error
                else: step = self._c1
        else:
            self._p1 -= 1
            self._x1 -= 1 if self._x1 > 0 else 0
            self._z1 -= 1 if not self.odd_round and self._z1 > 0 else 0

        return step

    def _c14b(self):
        print("running c14b")
        #print(self._s1, self._s2)
        step = self._c3a

        if self._p1 == 0:
            if not self._lsb:
                print('collaapsing lsb')
                collapsed = self._context.collapse_current_score_bracket()
                if not collapsed : step = self._pairing_error
                else: step = None
            else:
                print('collapsing previous score bracket')
                self._reset()
                collapsed = self._context.collapse_previous_score_bracket()
                if not collapsed: step = self._pairing_error
                else: step = self._c1
        elif self._paired_floaters and not self._lsb:
            print('reducing p1')
            self._p1 -= 1
            self._x1 -= 1 if self._x1 > 0 else 0
            self._z1 -= 1 if not self.odd_round and self._z1 > 0 else 0
        else:
            print('reducing m1 from', self._m1)
            if self._m1 > 1:
                self._m1 -= 1
                step = self._c3a
            elif self._m1 == 1:
                self._m1 = 0
                self._p1 = self._p0
                self._force_homogenous = True
                step = self._c2b

        return step

    def _pairing_error(self):
        print("Pairing Error")
        self._reset()
        step = None
        return step

class PairingCriteria:
    def __init__(self, score_bracket):
        self._score_bracket              = score_bracket
        self.b5_enabled_for_downfloaters = True
        self.b5_enabled_for_upfloaters   = True
        self.b6_enabled_for_downfloaters = True
        self.b6_enabled_for_upfloaters   = True
        self.a7d_enabled                 = True
        self.b2_enabled_for_top_scorers  = True

    def b1a(self, p1, p2):
        """p1 and p2 may not be paired if they have met before."""
        return p2.pairing_no not in p1.opponents

    def b1b(self, player):
        """player may not receive a bye if they received a bye already in the tournament."""
        return 0 not in player.opponents

    def b2(self, p1, p2):
        """p1 and p2 are incompatible if they have the same absolute colour preference."""
        abs_value = 1 if self._score_bracket.odd_round and self.a7d_enabled else 2
        p1_abs    = abs(p1.colour_preference) >= abs_value
        p2_abs    = abs(p2.colour_preference) >= abs_value

        half_max_score = self._score_bracket.round_no/2
        return (not(p1_abs) or not(p2_abs) or p1.colour_preference != p2.colour_preference
                or (self._score_bracket.last_round and not(self.b2_enabled_for_top_scorers)
                    and (p1.score > half_max_score or p2.score > half_max_score)))

    def b4(self, pairings):
        """The current pairings are acceptable if they satisfy the minimum number
        of colour preferences."""
        violated  = sum(p1.expected_colour == p2.expected_colour for (p1,p2) in pairings)
        return violated <= self._score_bracket.x

    def b5(self, p1, p2=None):
        """No player shall receive an identical float in two consecutive rounds."""
        def t1():
            return (p1.float_status != FloatStatus.down
                    if not(p2) and self.b5_enabled_for_downfloaters else True)
        def t2():
            return ((p1.score == p2.score 
                     or (p1.score < p2.score and p1.float_status != FloatStatus.up)
                     or (p1.score > p2.score and p2.float_status != FloatStatus.up))
                    if p2 and self.b5_enabled_for_upfloaters else True)
        return t1() and t2()

    def b6(self, p1, p2=None):
        """No player shall receive an identical float as two rounds before."""
        def t1(): 
            return (p1.float_status != FloatStatus.downPrev
                    if not(p2) and self.b6_enabled_for_downfloaters else True)
        def t2():
            return ((p1.score == p2.score
                     or (p1.score < p2.score and p1.float_status != FloatStatus.upPrev)
                     or (p1.score > p2.score and p2.float_status != FloatStatus.upPrev))
                    if p2 and self.b6_enabled_for_upfloaters else True)
        return t1() and t2()

    def satisfied(self, pairings, downfloater, bye):
        def t1():
            return all(self.b1a(p1, p2) and self.b2(p1, p2) and self.b5(p1, p2)
                       and self.b6(p1, p2) for (p1, p2) in pairings)
        def t2(): 
            return self.b4(pairings) if pairings else True
        def t3():
            return self.b5(downfloater) and self.b6(downfloater) if downfloater else True
        def t4():
           return self.b1b(bye) if bye else True
        #print('pairings: ', len(pairings), 'satisfied: ', t1() and t2() and t3() and t4() )
        return t1() and t2() and t3() and t4()

class PairingContext:
    def __init__(self, round_no, last_round, bye_value, score_brackets):
        self._ix             = 0
        self._round_no       = round_no
        self._last_round     = last_round
        self._bye_value      = bye_value
        self._score_brackets = score_brackets
        self._downfloaters   = []
        self._backtrackers   = []

    def __iter__(self):
        return self
    
    def __next__(self):
        try:
            result = self._score_brackets[self._ix]
            self._ix += 1
            return result
        except IndexError:
            raise StopIteration

    @property
    def round_no(self):
        return self._round_no

    @property
    def last_round(self):
        return self._last_round

    @property
    def bye_value(self):
        return self._bye_value

    @property
    def lowest_score_bracket(self):
        return self._index == len(self._score_brackets) - 1

    def collapse_current_score_bracket(self):
        for p in self._current_score_bracket.all_players:
            self._next_score_bracket.add_player(p)
        self._score_brackets.remove(self._current_score_bracket)
        self._ix -= 1
        return True

    def collapse_previous_score_bracket(self):
        if len(self._previous_score_bracket.all_players) == 0 :
            return False
        for p in self._previous_score_bracket.all_players:
            self._current_score_bracket.add_player(p)
        self._score_brackets.remove(self._previous_score_bracket)
        self._ix -= 1
        return True

    def can_downfloat(self, player):
        return (player not in self._downfloaters
                and not self.lowest_score_bracket)

    def downfloat(self, player):
        self._downfloaters.append(player)
        self._current_score_bracket.remove_player(player)
        self._next_score_bracket.add_player(player)

    def can_backtrack(self, player):
        return (player not in self._backtrackers
                and self._index != 0
                and self._previous_score_bracket.can_backtrack(player))

    def backtrack(self, player):
        self._backtrackers.append(player)
        self._current_score_bracket.remove_player(player)
        self._previous_score_bracket.backtrack(player)
        self._ix -= 2

    def finalize_pairings(self):
        for sb in self._score_brackets:
            sb.finalize_pairings()

    @property
    def _current_score_bracket(self):
        return self._score_brackets[self._index]

    @property 
    def _previous_score_bracket(self):
        return self._score_brackets[self._index-1] 

    @property
    def _next_score_bracket(self):
        return self._score_brackets[self._index+1]

    @property
    def _index(self):
        return self._ix - 1 if self._ix else self._ix
