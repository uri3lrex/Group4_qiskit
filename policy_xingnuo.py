from qnetsim import bbpssw


class BaselinePolicy:
    def __init__(self, params):
        self.params = params
        self.chains = params["policy"]["swap_chains"]

    def on_pair_ready(self, link, pair, state, sim):
        for left, right in self.chains:
            if state.pairs.get(left) and state.pairs.get(right):
                sim.swap(left, right)


class FidelityPolicy(BaselinePolicy):
    def on_pair_ready(self, link, pair, state, sim):
        target_fidelity = self.params["slo"]["min_fidelity"]
        for link_id in state.pairs:
            inventory = state.pairs[link_id] # pairs on link_id
            index = 0

            # Filter pairs where the value of current_fidelity is greater than 0.5
            while index < len(inventory):
                if state.current_fidelity(inventory[index]) <= 0.5: # a pair that does not meet the final fidelity target may still be useful for purification
                    sim.discard(link_id, index)
                else:
                    index += 1

            if state.purification_allowed:
                while len(inventory) >= 3: # Purification may produce one improved pair if successful, or lose both input pairs if unsuccessful.
                                           # Having a third pair provides a backup.
                                           
                    # Find the pair and the index with the highest fidelity                       
                    best_index = 0
                    best_fidelity = state.current_fidelity(inventory[0])
                    for index in range(1, len(inventory)):
                        fidelity = state.current_fidelity(inventory[index])
                        if fidelity > best_fidelity:
                            best_index = index
                            best_fidelity = fidelity
                    if best_index < 2: # the highest-fidelity pair must not be among the first two pairs
                        break

                    # only attempt to purify the first two pairs
                    first_fidelity = state.current_fidelity(inventory[0])
                    second_fidelity = state.current_fidelity(inventory[1])
                    input_fidelity = min(first_fidelity, second_fidelity)
                    purified_fidelity, success_probability = bbpssw(input_fidelity)
                    if purified_fidelity <= input_fidelity:
                        break
                    sim.purify(link_id)

        for left, right in self.chains:
            while state.pairs.get(left) and state.pairs.get(right):

                # find the entangled pair with the highest current fidelity on each link
                left_pairs = state.pairs[left]
                left_index = 0
                left_fidelity = state.current_fidelity(left_pairs[0])
                for index in range(1, len(left_pairs)):
                    fidelity = state.current_fidelity(left_pairs[index])
                    if fidelity > left_fidelity:
                        left_index = index
                        left_fidelity = fidelity

                right_pairs = state.pairs[right]
                right_index = 0
                right_fidelity = state.current_fidelity(right_pairs[0])
                for index in range(1, len(right_pairs)):
                    fidelity = state.current_fidelity(right_pairs[index])
                    if fidelity > right_fidelity:
                        right_index = index
                        right_fidelity = fidelity

                estimated_fidelity = left_fidelity * right_fidelity * state.f_swap
                purification_link = None
                best_gain = 0.0
                if state.purification_allowed and estimated_fidelity < target_fidelity:

                    # test and decide which link to purify
                    for link_id in (left, right):
                        inventory = state.pairs[link_id]
                        if len(inventory) < 2:
                            continue
                        first_fidelity = state.current_fidelity(inventory[0])
                        second_fidelity = state.current_fidelity(inventory[1])
                        input_fidelity = min(first_fidelity, second_fidelity)
                        purified_fidelity, success_probability = bbpssw(input_fidelity)
                        if link_id == left:
                            improved_fidelity = (purified_fidelity * right_fidelity
                                                  * state.f_swap)
                        else:
                            improved_fidelity = (left_fidelity * purified_fidelity
                                                  * state.f_swap)
                        gain = (improved_fidelity - estimated_fidelity) * success_probability
                        if gain > best_gain:
                            best_gain = gain
                            purification_link = link_id
                if purification_link is not None:
                    sim.purify(purification_link)
                else:
                    sim.swap(left, right, left_index=left_index,
                             right_index=right_index)


def make_policy(params):
    return FidelityPolicy(params)
