import settings

networkStatus = {}  # Dict that will contain the status of every agent in the network

# Initialize agent states. Let's assume everyone is normal and all types are population.
init_states = [{'id': 0, 'type': 0, 'rad': 0, 'fstatus':0,  } for _ in range(settings.network_params["number_of_nodes"])]

