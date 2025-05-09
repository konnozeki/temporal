from temporalio.client import Client

client_instance: Client = None


def set_client(client: Client):
    global client_instance
    client_instance = client


async def get_client() -> Client:
    if not client_instance:
        raise RuntimeError("Temporal client not initialized")
    return client_instance
