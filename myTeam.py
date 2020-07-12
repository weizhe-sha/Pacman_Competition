# myTeam.py
# ---------
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley, including a link to http://ai.berkeley.edu.
#
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).

import sys

sys.path.append('teams/Procrastinating/')
from captureAgents import CaptureAgent
import random, time, util
from game import Directions
import game
from util import nearestPoint


#################
# Team creation #
#################

DEPTH = 10

def createTeam(firstIndex, secondIndex, isRed,
               first='AttackAgent', second='AttackAgent'):
    """
  This function should return a list of two agents that will form the
  team, initialized using firstIndex and secondIndex as their agent
  index numbers.  isRed is True if the red team is being created, and
  will be False if the blue team is being created.

  As a potentially helpful development aid, this function can take
  additional string-valued keyword arguments ("first" and "second" are
  such arguments in the case of this function), which will come from
  the --redOpts and --blueOpts command-line arguments to capture.py.
  For the nightly contest, however, your team will be created without
  any extra arguments, so you should make sure that the default
  behavior is what you want for the nightly contest.
  """

    # The following line is an example only; feel free to change it.
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


##########
# Agents #
##########

class ReflexCaptureAgent(CaptureAgent):
    """
    A Dummy agent to serve as an example of the necessary agent structure.
    You should look at baselineTeam.py for more details about how to
    create an agent as this is the bare minimum.
    """

    def registerInitialState(self, gameState):
        """
    This method handles the initial setup of the
    agent to populate useful fields (such as what team
    we're on).

    A distanceCalculator instance caches the maze distances
    between each pair of positions, so your agents can use:
    self.distancer.getDistance(p1, p2)

    IMPORTANT: This method may run for at most 15 seconds.
    """

        '''
    Make sure you do not delete the following line. If you would like to
    use Manhattan distances instead of maze distances in order to save
    on initialization time, please take a look at
    CaptureAgent.registerInitialState in captureAgents.py.
    '''
        CaptureAgent.registerInitialState(self, gameState)

        '''
    Your initialization code goes here, if you need any.
    '''
        self.start = gameState.getAgentPosition(self.index)

    def getSuccessor(self, gameState, action):
        """
    Finds the next successor which is a grid position (location tuple).
    """
        successor = gameState.generateSuccessor(self.index, action)
        pos = successor.getAgentState(self.index).getPosition()
        if pos != nearestPoint(pos):
            return successor.generateSuccessor(self.index, action)
        else:
            return successor

    def evaluate(self, gameState, action):
        """
    Computes a linear combination of features and feature weights
    """
        features = self.getFeatures(gameState, action)
        weights = self.getWeights(gameState, action)
        return features * weights

    def getFeatures(self, gameState, action):
        """
    Returns a counter of features for the state
    """
        features = util.Counter()
        successor = self.getSuccessor(gameState, action)
        features['successorScore'] = self.getScore(successor)

        return features

    def getWeights(self, gameState, action):

        return {'successorScore': 1.0}

    def leadToDeadEnd(self, gameState, action, depth):
        if depth == 0:
            return False
        new_state = self.getSuccessor(gameState, action)
        score_before = self.getScore(gameState)
        score_after = self.getScore(new_state)
        if score_before < score_after:
            return False
        actions = new_state.getLegalActions(self.index)
        actions.remove(Directions.STOP)
        reversed_direction = Directions.REVERSE[new_state.getAgentState(self.index).configuration.direction]
        if reversed_direction in actions:
            actions.remove(reversed_direction)
        if len(actions) == 0:
            return True
        for a in actions:
            if self.leadToDeadEnd(new_state, a, depth - 1) == 0:
                return False
        return True


class AttackAgent(ReflexCaptureAgent):

    def registerInitialState(self, gameState):
        CaptureAgent.registerInitialState(self, gameState)
        self.start = gameState.getAgentPosition(self.index)
        self.team = self.getTeam(gameState)
        self.roles = {}
        self.visitedTimes = util.Counter()

        self.target = None
        self.foodLeft = self.getFoodYouAreDefending(gameState).asList()
        self.borderDict = {}

        for index in self.team:
            self.roles[index] = "attacker"

        if self.red:
            border_x = int((gameState.data.layout.width - 2) / 2)
        else:
            border_x = int(((gameState.data.layout.width - 2) / 2) + 1)

        self.border = []
        for i in range(1, gameState.data.layout.height - 1):
            if not gameState.hasWall(border_x, i):
                self.border.append((border_x, i))

        self.calculate_prob(gameState)


    def getFeatures(self, gameState, action):
        features = util.Counter()
        successor = self.getSuccessor(gameState, action)
        foodList = self.getFood(successor).asList()
        features['successorScore'] = -len(foodList)  # self.getScore(successor)
        new_state = successor.getAgentState(self.index)


        if new_state.numCarrying > 0:
            features['successorScore'] = self.getScore(successor)
        new_pos = new_state.getPosition()
        features['visitedTimes'] = self.visitedTimes[new_pos]
        if self.getMazeDistance(new_pos, self.start) > 10:
            features['distanceToHome'] = self.getMazeDistance(new_pos, self.start)
        else:
            features['distanceToHome'] = 1000
        if len(foodList) > 0:
            minDistance = min([self.getMazeDistance(new_pos, food) for food in foodList])
            features['distanceToFood'] = minDistance
        successor.getAgentDistances()
        enemies = [successor.getAgentState(i) for i in self.getOpponents(successor)]
        ghosts = [a for a in enemies if not a.isPacman and a.getPosition() != None]
        if len(ghosts) > 0:
            dists = [self.getMazeDistance(new_pos, a.getPosition()) for a in ghosts]
            features['ghostDistance'] = min(dists)
            index = dists.index(min(dists))
            direction = ghosts[index].getDirection()
            position = ghosts[index].getPosition()
            if action == direction:
                features['ghostDirection'] = 1
            current_position = gameState.getAgentPosition(self.index)
            if new_pos[0] == position[0] and new_pos[1] == position[1] or \
                    self.getMazeDistance(current_position,new_pos) > 1:
                features['collideIntoGhost'] = 1
        else:
            enemies_distances = [successor.getAgentDistances()[i] for i in self.getOpponents(successor)]
            features['ghostDistance'] = min(enemies_distances)

        rev = Directions.REVERSE[gameState.getAgentState(self.index).configuration.direction]
        if action == rev: features['reverse'] = 1

        features['isGhost'] = 0 if successor.getAgentState(self.index).isPacman else 1

        return features

    def getWeights(self, gameState, action):
        weights = util.Counter()
        successor = self.getSuccessor(gameState, action)
        new_state = successor.getAgentState(self.index)
        new_pos = new_state.getPosition()

        enemies = [successor.getAgentState(i) for i in self.getOpponents(successor)]
        ghosts = [a for a in enemies if not a.isPacman and a.getPosition() is not None and a.scaredTimer <5]
        if len(ghosts) > 0:
            if not new_state.isPacman:
                weights['visitedTimes'] = -5
            dists = [self.getMazeDistance(new_pos, a.getPosition()) for a in ghosts]
            closest_enemies = [a for a, dist in zip(ghosts, dists) if dist == min(dists)]
            for enemy in closest_enemies:
                if enemy.scaredTimer > 0:
                    return {'successorScore': 100, 'distanceToFood': -10}
        elif not new_state.isPacman:
            weights['visitedTimes'] = -3
        weights['successorScore'] = 100
        weights['ghostDistance'] = 5
        weights['ghostDirection'] = 100
        weights['isGhost'] = 10000
        weights['distanceToHome'] = -10
        weights['reverse'] = -2
        weights['collideIntoGhost'] = -1000
        return weights


    def rollout(self, iteration, gameState):
        new_state = gameState.deepCopy()
        value = 0
        while iteration > 0:
            actions = new_state.getLegalActions(self.index)
            actions.remove(Directions.STOP)
            direct = new_state.getAgentState(self.index).configuration.direction
            rev = Directions.REVERSE[direct]
            if rev in actions and len(actions) > 1:
                actions.remove(rev)
            a = random.choice(actions)
            value += (0.1 ** (DEPTH - iteration)) * self.evaluate(new_state, a)
            new_state = self.getSuccessor(new_state,a)
            iteration -= 1
        actions = new_state.getLegalActions(self.index)
        a = random.choice(actions)
        value += (0.1 ** (DEPTH - iteration)) * self.evaluate(new_state, a)
        return value


    def calculate_prob(self, gameState):
        foods = self.getFoodYouAreDefending(gameState).asList()
        prob_list = []

        for position in self.border:
            dist = min([self.getMazeDistance(position, food) for food in foods])
            if dist == 0:
                dist = 1
            prob_list.append(1.0 / float(dist))

        total = sum(prob_list)

        if sum(prob_list) == 0:
            for pos, prob in zip(self.border,prob_list):
                self.borderDict[pos] = prob
        else:
            for pos, prob in zip(self.border,prob_list):
                self.borderDict[pos] = float(prob) / float(total)

    def all_defenders(self, gameState):
        for index in self.team:
            if gameState.getAgentState(index).isPacman:
                return False
        return True

    def all_pacman(self, gameState):
        for index in self.team:
            if not gameState.getAgentState(index).isPacman:
                return False
        return True

    def all_attackers(self):
        for index in self.team:
            if not self.roles[index] == "attacker":
                return False
        return True

    def all_onborders(self, gameState):
        for index in self.team:
            if not gameState.getAgentPosition(index):
                return False
        return True

    def randomWithWeight(self, weighted):
        total = sum(weighted.values())
        r = random.uniform(0, total)
        accumulator = 0
        for k in weighted.keys():
            accumulator += weighted[k]
            if accumulator >= r:
                return k

    def bestActionToTarget(self, gameState):
        dist = self.getMazeDistance(gameState.getAgentState(self.index).getPosition(), self.target)
        # legalActions = gameState.getLegalActions(self.index)
        for a in gameState.getLegalActions(self.index):
            if a == Directions.STOP:
                # legalActions.remove(a)
                continue
            successor = self.getSuccessor(gameState, a)
            if successor.getAgentState(self.index).isPacman:
                # legalActions.remove(a)
                continue
            if self.getMazeDistance(successor.getAgentState(self.index).getPosition(), self.target) < dist:
                return a
        return None

    def chooseAction(self, gameState):
        myPos = gameState.getAgentPosition(self.index)
        foodtoEat = len(self.getFood(gameState).asList())
        myState = gameState.getAgentState(self.index)
        all_actions = gameState.getLegalActions(self.index)
        all_actions.remove(Directions.STOP)
        enemies = [gameState.getAgentState(i) for i in self.getOpponents(gameState)]
        ghosts = [a for a in enemies if not a.isPacman and a.getPosition() is not None and not a.scaredTimer > 5]
        invaders = [a for a in enemies if a.isPacman and a.getPosition() is not None]
        self.visitedTimes[myPos] += 1

        if len((self.foodLeft)) > len(self.getFoodYouAreDefending(gameState).asList()):
            if self.all_pacman(gameState):
                if self.index < 2:
                    self.roles[self.index] = "attacker"
                    for index in self.team:
                        if not index == self.index:
                            self.roles[index] = "defender"
                else:
                    self.roles[self.index] = "defender"
                    for index in self.team:
                        if not index == self.index:
                            self.roles[index] = "attacker"

            elif self.all_attackers():
                if self.index < 2:
                    self.roles[self.index] = "attacker"
                    for index in self.team:
                        if not index == self.index:
                            self.roles[index] = "defender"
                else:
                    self.roles[self.index] = "defender"
                    for index in self.team:
                        if not index == self.index:
                            self.roles[index] = "attacker"
        elif self.roles[self.index] == "defender":
            if len(self.observationHistory) > 2:
                our_states = [gameState.getAgentState(i) for i in self.team]
                our_pos = [state.getPosition() for state in our_states]
                old_invaders = [self.observationHistory[-2].getAgentState(i) for i in self.getOpponents(gameState) if
                                self.observationHistory[-2].getAgentState(i).isPacman]
                old_invader_pos = [invader.getPosition() for invader in old_invaders]
                if not set(our_pos).isdisjoint(old_invader_pos) and not len(invaders) > 0:
                    if not self.index < 2:
                        self.foodLeft = self.getFoodYouAreDefending(gameState).asList()
                        self.roles[self.index] = "attacker"

        if self.roles[self.index] == "defender" or \
                (len(invaders) > 0 and not myState.isPacman):
            if myState.isPacman:
                if len(ghosts) > 0:
                    dists = [self.getMazeDistance(myPos, a.getPosition()) for a in ghosts]
                    if len(self.getCapsules(gameState)) > 0:
                        cap_dists = [self.getMazeDistance(myPos, capsule) for capsule in self.getCapsules(gameState)]
                        if min(cap_dists) <= min(dists) - 1:
                            if self.goToCapsules(gameState, all_actions, min(cap_dists)) is not None:
                                return self.goToCapsules(gameState, all_actions, min(cap_dists))
                    if min(dists) < 10:
                        if self.bestActionToHome(gameState, all_actions) is not None:
                            return self.bestActionToHome(gameState, all_actions)

            foodDefending = self.getFoodYouAreDefending(gameState).asList()
            if gameState.getAgentState(self.index).getPosition() == self.target:
                self.target = None
            if self.target is None:
                if len(foodDefending) > 4:
                    weighted = {}
                    for i in self.border:
                        minDistToFood = 9999
                        for f in foodDefending:
                            distToFood = self.getMazeDistance(i, f)
                            if distToFood < minDistToFood:
                                minDistToFood = distToFood
                        if minDistToFood == 0.0:
                            minDistToFood = 1.0
                        weighted[i] = 1.0 / minDistToFood
                    self.target = self.randomWithWeight(weighted)
                else:
                    remained = foodDefending + self.getCapsulesYouAreDefending(gameState)
                    self.target = random.choice(remained)
            opponentsState = []
            for i in self.getOpponents(gameState):
                opponent = gameState.getAgentState(i)
                opponentsState.append(opponent)
            minDistToOppo = 9999
            for oppo in opponentsState:
                oppoPos = oppo.getPosition()
                if oppo.isPacman:
                    if oppoPos is not None:
                        if minDistToOppo > self.getMazeDistance(gameState.getAgentState(self.index).getPosition(),
                                                                oppoPos):
                            minDistToOppo = self.getMazeDistance(gameState.getAgentState(self.index).getPosition(),
                                                                 oppoPos)
                            self.target = oppoPos
                    else:
                        if len(foodDefending) < len(self.foodLeft) and set(self.foodLeft).issuperset(set(foodDefending)):
                            foodEaten = set(self.foodLeft).difference(set(foodDefending))
                            self.target = random.choice(tuple(foodEaten))
            self.foodLeft = foodDefending
            if self.bestActionToTarget(gameState) is not None:
                return self.bestActionToTarget(gameState)
            else:
                if self.bestActionToHome(gameState, all_actions) is not None:
                    return self.bestActionToHome(gameState, all_actions)


        if len(ghosts) > 0:
            dists = [self.getMazeDistance(myPos, a.getPosition()) for a in ghosts]
            if len(self.getCapsules(gameState)) > 0:
                cap_dists = [self.getMazeDistance(myPos, capsule) for capsule in self.getCapsules(gameState)]
                if min(cap_dists) <= min(dists) - 1:
                    if self.goToCapsules(gameState, all_actions, min(cap_dists)) is not None:
                        return self.goToCapsules(gameState, all_actions, min(cap_dists))
                    else:
                        return random.choice(all_actions)
            if min(dists) < 10:
                if self.bestActionToHome(gameState, all_actions) is not None:
                    return self.bestActionToHome(gameState, all_actions)

        if foodtoEat == 0 or \
                gameState.data.timeleft < min([self.getMazeDistance(myPos, home) for home in self.border])*4+4:
            bestDist = 9999
            for action in all_actions:
                successor = self.getSuccessor(gameState, action)
                pos2 = successor.getAgentPosition(self.index)
                dists = [self.getMazeDistance(home, pos2) for home in self.border]
                if min(dists) < bestDist:
                    best_action = action
                    bestDist = min(dists)
            return best_action

        minFoodDist = 9999
        minFoodPos = (0, 0)

        if len(self.getFood(gameState).asList()) > 0:
            for food in self.getFood(gameState).asList():
                if self.getMazeDistance(gameState.getAgentPosition(self.index), food) < minFoodDist:
                    minFoodDist = self.getMazeDistance(gameState.getAgentPosition(self.index), food)
                    minFoodPos = food


        for a in all_actions:
            nextAgentState = self.getSuccessor(gameState,a)
            next_pos = nextAgentState.getAgentPosition(self.index)
            if self.getMazeDistance(next_pos, minFoodPos) < minFoodDist:
                # print("eating food")
                return a
        return random.choice(all_actions)


    def goToCapsules(self, gameState, actions, num):
        for action in actions:
            successor = self.getSuccessor(gameState, action)
            next_pos = successor.getAgentPosition(self.index)
            if next_pos in self.getCapsules(gameState):
                return action
            cap_dists = [self.getMazeDistance(next_pos, capsule) for capsule in self.getCapsules(successor)]
            if len(cap_dists) > 0:
                if min(cap_dists) < num:
                    return action
            else:
                return None

    def bestActionToHome(self, gameState, actions):
        enemies = [gameState.getAgentState(i) for i in self.getOpponents(gameState)]
        ghosts = [a for a in enemies if not a.isPacman and a.getPosition() != None and not a.scaredTimer > 5]
        values = util.Counter()

        for action in actions:
            value = 0
            successor = self.getSuccessor(gameState, action)
            next_pos = successor.getAgentPosition(self.index)
            ghost_dists = [self.getMazeDistance(next_pos, a.getPosition()) for a in ghosts]
            deadend = self.leadToDeadEnd(gameState,action,10)
            if deadend and len(ghost_dists) > 0:
                # print("remove action to dead end:" + str(action))
                continue

            if len(ghost_dists) > 0:
                if min(ghost_dists) < 2:
                    # print("remove action close to ghosts:" + str(action))
                    continue
            for i in range(5):
                value += self.rollout(7,successor)
            values[action] = value

        all = values.items()
        list = [x[1] for x in all]
        if len(list) == 0:
            return None
        best = [action for action,value in all if value == max(list)]
        return best[0]