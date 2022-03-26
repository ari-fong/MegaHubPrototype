from enum import Enum
from enum import auto


class SubnetMessage(Enum):
    ADD_TARGETS    = auto()
    REMOVE_TARGETS = auto()
    ADD_ROUTERS    = auto()
    REMOVE_ROUTERS = auto()
    ACTIVATE_HUB   = auto()
    DEACTIVATE_HUB = auto()


class Network:
    def __init__(self, routers, targets):
        self.routers = {router_id: self.subnet_id_from_router_id(router_id) for router_id in routers}
        self.targets = {target_id: None for target_id in targets}

    def move_targets(self, targets, new_subnet_id=None):
        print('')
        print(f'MOVING TARGETS {targets} TO SUBNET {new_subnet_id}')
        removed_targets_by_subnet = dict()
        for target in targets:
            old_subnet_id = self.targets[target]
            if old_subnet_id is not None:
                # If we are moving multiple targets from that subnet, batch them
                if old_subnet_id in removed_targets_by_subnet:
                    removed_targets_by_subnet[old_subnet_id].append(target)
                else:
                    removed_targets_by_subnet[old_subnet_id] = [target]
            self.targets[target] = new_subnet_id

        if new_subnet_id is not None:
            self.send_message(new_subnet_id,
                              SubnetMessage.ADD_TARGETS,
                              {'targets': targets})
        for old_subnet_id, removed_targets in removed_targets_by_subnet.items():
            self.send_message(old_subnet_id,
                              SubnetMessage.REMOVE_TARGETS,
                              {'targets': removed_targets})
        self.print()

    def move_routers(self, routers, new_subnet_id=None):
        print('')
        print(f'MOVING ROUTERS {routers} TO SUBNET {new_subnet_id}')
        removed_routers_by_subnet = dict()
        if new_subnet_id is not None:
            if new_subnet_id not in self.routers.values():
                # This is a new subnet with no routers in it yet
                # TODO: Do we want an option that means "new subnet" so that
                #       we can assign a correct subnet id automatically?
                hub_router = self.router_id_from_subnet_id(new_subnet_id)
                assert hub_router in routers, f"Not a valid subnet ID {new_subnet_id}"
                self.send_message(new_subnet_id,
                                  SubnetMessage.ACTIVATE_HUB,
                                  {'routers': routers,
                                   'targets': []})
            self.send_message(new_subnet_id,
                              SubnetMessage.ADD_ROUTERS,
                              {'routers': routers})

        for router in routers:
            old_subnet_id = self.routers[router]
            if old_subnet_id in removed_routers_by_subnet:
                removed_routers_by_subnet[old_subnet_id].append(router)
            else:
                removed_routers_by_subnet[old_subnet_id] = [router]
            self.routers[router] = new_subnet_id

        for old_subnet_id, removed_routers in removed_routers_by_subnet.items():
            remaining_routers = self.get_routers_in_subnet(old_subnet_id)
            remaining_targets = self.get_targets_in_subnet(old_subnet_id)
            if remaining_routers:
                # There are still routers on this old subnet
                if self.router_id_from_subnet_id(old_subnet_id) in removed_routers:
                    # The hub is moving out of the old subnet
                    self.send_message(old_subnet_id,
                                      SubnetMessage.DEACTIVATE_HUB,
                                      {})

                    # Make a new subnet with the remaining routers and targets
                    corrected_subnet_id = self.subnet_id_from_router_id(min(remaining_routers))
                    for router in remaining_routers:
                        self.routers[router] = corrected_subnet_id
                    for target in remaining_targets:
                        self.targets[target] = corrected_subnet_id
                    self.send_message(corrected_subnet_id,
                                      SubnetMessage.ACTIVATE_HUB,
                                      {'routers': remaining_routers,
                                       'targets': remaining_targets})
                else:
                    # The hub was not removed from the subnet
                    self.send_message(old_subnet_id,
                                      SubnetMessage.REMOVE_ROUTERS,
                                      {'routers': removed_routers})
            else:
                # No routers left in subnet
                self.send_message(old_subnet_id,
                                  SubnetMessage.DEACTIVATE_HUB,
                                  {})
                for target in remaining_targets:
                    self.targets[target] = None
        self.print()

    def subnet_id_from_router_id(self, router_id):
        # Hub id convention: maybe change later?
        return router_id - 1

    def router_id_from_subnet_id(self, subnet_id):
        # Hub id convention: maybe change later?
        return subnet_id + 1

    def get_routers_in_subnet(self, subnet_id):
        return [router for router, subnet in self.routers.items()
                if subnet == subnet_id]

    def get_targets_in_subnet(self, subnet_id):
        return [target for target, subnet in self.targets.items()
                if subnet == subnet_id]

    def send_message(self, subnet_id, message_type, data):
        # This should tell the subnet hub what routers or targets should be added or removed,
        # or when to activate or deactivate the entire subnetwork.
        # The subnet hub should update its own routers and state accordingly.
        print(f'Sending {message_type} command to subnet {subnet_id}, '
              f'data: {data}')

    def print(self):
        subnets = sorted(set(self.routers.values()))
        for subnet in subnets:
            print(f'Subnet {subnet}: {self.get_routers_in_subnet(subnet)} -> {self.get_targets_in_subnet(subnet)}')

    # Will there be any concept of dormant hubs in this new system?
    # No. Dormant hubs are inherently unstable.
    # Much better to rely on db data for setup and step, or even just
    # setup if indeed we're planning on making the optimization very fast.
    # Really I'm finding that this will require:
    # a) A very fast network connection step, or
    # b) The megahub to be connected to all subnet hubs.

    # Thought about wheel_update: I hate everything to do with Dormant Hubs.
    # They're fragile and difficult.
    # It seems to me that it would be better to have new hubs spin up from
    # database-stored status. But then I guess we couldn't have isolated
    # networks. Regardless, less granular control. Maybe cut out higher level
    # SMs and just have dormant hubs sit in App and know the state and spokes.
    # What other things could we skip reliance on event queues and rely on DBs
    # for?
    # Dash update request could set a flag that gets pushed down when handled
    # instead of handled every time, so they are only handled as fast as the
    # App can deal with them


routers = [3, 5, 7, 9]
targets = [1, 2, 3, 4]
network = Network(routers=routers, targets=targets)
network.print()
network.move_targets([1, 3], 2)
network.move_targets([2, 4], 4)
network.move_routers([5, 7], 2)
network.move_targets([2, 3, 4], 8)
network.move_routers([3], 8)
network.move_routers([7], 8)
network.move_routers([9], 4)
network.move_routers([5, 7], 6)
network.move_routers([5, 9], 6)

