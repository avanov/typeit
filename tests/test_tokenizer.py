import requests
import vcr
from typing import NamedTuple, Sequence, Mapping, Generator, Type, Any

from tests.paths import VCR_FIXTURES_PATH
from typeit import TypeConstructor
from typeit.tokenizer import iter_tokens, Token


def test_tokenizer():

    class Language(NamedTuple):
        code: str
        name: str

    class Country(NamedTuple):
        code: str
        name: str
        languages: Sequence[Language]

    class CountriesQuery(NamedTuple):
        countries: Sequence[Country]


    mk_countries_query, dict_countries_query = TypeConstructor  ^ CountriesQuery

    translate_begin_type = lambda x: f'{x.python_name} {{'
    translate_begin_type_inner = lambda x: '{'
    translate_end_type = lambda x: '}'
    translate_begin_attribute = lambda x: f'{x.wire_name}'
    translate_end_attribute = lambda x: ' '

    translation_map: Mapping[Token, str] = {
        Token.BeginType: translate_begin_type,
        Token.EndType:  translate_end_type,
        Token.BeginAttribute: translate_begin_attribute,
        Token.EndAttribute: translate_end_attribute,
    }

    def translate_tokens_to_graphql(typ: Type[Any]) -> Generator[str, None, None]:
        """ for graphql queries BeginType should be translated only once - for the topmost type
        """
        query_type_began = False
        for token in iter_tokens(typ, typer=TypeConstructor):
            for token_type, do_translate in translation_map.items():
                if isinstance(token, token_type):
                    if token_type is Token.BeginType:
                        if query_type_began:
                            yield translate_begin_type_inner(token)
                        else:
                            query_type_began = True
                            yield do_translate(token)
                    else:
                        yield do_translate(token)
                    break
            else:
                raise ValueError(f'Unhandled token: {token}')

    translation = lambda x: ''.join(translate_tokens_to_graphql(x))

    graphql_query = translation(CountriesQuery)
    assert graphql_query
    graphql_query = f'query {graphql_query}'

    with vcr.use_cassette(str(VCR_FIXTURES_PATH / 'countries.yaml')):
        response = requests.post(
            url='https://countries.trevorblades.com/',
            json={
                "operationName": f"{CountriesQuery.__name__}",
                "variables": {},
                "query": graphql_query,
            },
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': 'https://countries.trevorblades.com',
            }
        )
    response.raise_for_status()
    data = response.json()['data']
    assert data
    typed_data = mk_countries_query(data)
    assert isinstance(typed_data, CountriesQuery)

