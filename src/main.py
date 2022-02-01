import os

from dotenv import load_dotenv
from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport

from get_meta import get_meta
from choise import check

load_dotenv()


def make_client() -> Client:
    access_token = os.getenv("GITHUB_ACCESS_TOKEN")
    transport = AIOHTTPTransport(
        url="https://api.github.com/graphql",
        headers={"Content-type": "application/json", "Authorization": "Bearer {}".format(access_token)},
    )
    return Client(transport=transport, fetch_schema_from_transport=True)


def main():
    client = make_client()
    get_meta(client)
    check()


if __name__ == '__main__':
    main()
