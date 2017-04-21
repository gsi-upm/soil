import settings

networkStatus = {}  # Dict that will contain the status of every agent in the network

sentimentCorrelationNodeArray = []
for x in range(0, settings.number_of_nodes):
    sentimentCorrelationNodeArray.append({'id': x})
# Initialize agent states. Let's assume everyone is normal.
init_states = [{'id': 0, } for _ in range(settings.number_of_nodes)]
    # add keys as as necessary, but "id" must always refer to that state category
