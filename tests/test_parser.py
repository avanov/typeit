import json
from enum import Enum
from typing import NamedTuple, Dict, Any, Sequence, Union, Tuple, Optional, Set, List, FrozenSet, get_type_hints

import colander
import pytest
from money.currency import Currency
from money.money import Money

from typeit import codegen as cg
from typeit import parser as p
from typeit.sums import SumType, Variant


def test_parser_empty_struct():
    struct = {}
    parsed, overrides = cg.parse(struct)
    struct, overrides_ = cg.construct_type('main', parsed)
    overrides.update(overrides_)
    assert overrides == {}
    python_src, __ = cg.codegen_py(struct, overrides, False)
    assert python_src == "class Main(NamedTuple):\n    ...\n\n"


def test_typeit():
    x = {}
    cg.typeit(x)


def test_type_with_unclarified_list():
    class X(NamedTuple):
        x: Sequence
        y: List

    mk_main, dict_main = p.type_constructor(X)
    x = mk_main({'x': [], 'y': []})
    x = mk_main({'x': [1], 'y': ['1']})
    assert x.x[0] == int(x.y[0])
    x = mk_main({'x': ['Hello'], 'y': ['World']})
    assert f'{x.x[0]} {x.y[0]}' == 'Hello World'


def test_type_with_sequence():
    class X(NamedTuple):
        x: int
        y: Sequence[Any]
        z: Sequence[str]

    mk_main, serializer = p.type_constructor(X)

    x = mk_main({'x': 1, 'y': [], 'z': ['Hello']})
    assert x.y == []
    assert x.z[0] == 'Hello'


def test_type_with_tuple_primitives():
    # There are several forms of tuple declarations
    # https://docs.python.org/3/library/typing.html#typing.Tuple
    # We want to support all possible fixed-length tuples,
    # including empty one
    class X(NamedTuple):
        a: Tuple[str, int]  # fixed N-tuple
        b: Tuple            # the following are equivalent
        c: tuple

    mk_x, serializer = p.type_constructor(X)

    x = mk_x({
        'a': ['value', '5'],
        'b': (),
        'c': [],
        'd': ['Hello', 'Random', 'Value', 5, None, True, {}],
    })
    assert x.a == ('value', 5)
    assert x.b == ()
    assert x.b == x.c

    with pytest.raises(colander.Invalid):
        # 'abc' is not int
        x = mk_x({
            'a': ['value', 'abc'],
            'b': [],
            'c': [],
        })

    with pytest.raises(colander.Invalid):
        # .c field is required
        x = mk_x({
            'a': ['value', 5],
            'b': [],
        })

    with pytest.raises(colander.Invalid):
        # .c field is required to be fixed sequence
        x = mk_x({
            'a': ['value', 'abc'],
            'b': (),
            'c': None,
        })


def test_type_with_complex_tuples():
    class Y(NamedTuple):
        a: Dict

    class X(NamedTuple):
        a: Tuple[Tuple[Dict, Y], int]
        b: Optional[Any]

    mk_x, serializer = p.type_constructor(X)

    x = mk_x({
        'a': [
            [{}, {'a': {'inner': 'value'}}],
            5
        ],
    })
    assert isinstance(x.a[0][1], Y)
    assert isinstance(x.a[1], int)
    assert x.b is None

    x = mk_x({
        'a': [
            [{}, {'a': {'inner': 'value'}}],
            5
        ],
        'b': Y(a={})
    })
    assert isinstance(x.b, Y)


def test_unsupported_variable_length_tuples():
    class X(NamedTuple):
        a: Tuple[int, ...]

    with pytest.raises(TypeError):
        mk_x, dict_x = p.type_constructor(X)


def test_enum_like_types():
    class Enums(Enum):
        A = 'a'
        B = 'b'

    class Sums(SumType):
        A: Variant[str]
        B: Variant[str]

    class X(NamedTuple):
        e: Enums
        s: Sums

    mk_x, dict_x = p.type_constructor(X)

    data = {'e': 'a', 's': 'b'}
    x = mk_x(data)
    assert isinstance(x.e, Enums)
    assert isinstance(x.s, Sums)
    assert isinstance(x.s('value'), Sums)
    assert data == dict_x(x)

    with pytest.raises(colander.Invalid):
        x = mk_x({'e': 'a', 's': None})


def test_enum_unions_serialization():
    class E0(Enum):
        A = 'a'
        B = 'b'
        C = 'C'

    class E1(Enum):
        X = 'x'
        Y = 'y'
        Z = 'z'


    class MyType(NamedTuple):
        val: Union[E0, E1]


    __, serializer = p.type_constructor(MyType)

    assert serializer(MyType(val=E1.Z)) == {'val': 'z'}


def test_type_with_empty_enum_variant():
    class Types(Enum):
        A = ''
        B = 'b'

    class X(NamedTuple):
        x: int
        y: Types

    mk_x, serializer = p.type_constructor(X)

    for variant in Types:
        x = mk_x({'x': 1, 'y': variant.value})
        assert x.y is variant

    with pytest.raises(colander.Invalid):
        x = mk_x({'x': 1, 'y': None})


def test_type_with_set():
    class X(NamedTuple):
        a: FrozenSet
        b: FrozenSet[Any]
        c: frozenset
        d: FrozenSet[int]
        e: set
        f: Set
        g: Set[Any]
        h: Set[int]

    mk_x, serializer = p.type_constructor(X)

    x = mk_x({
        'a': [],
        'b': [],
        'c': [],
        'd': [1],
        'e': [],
        'f': [],
        'g': [],
        'h': ['1'],
    })
    assert x.a == x.b == x.c == frozenset()
    assert isinstance(x.d, frozenset)
    assert isinstance(x.e, set)
    assert x.h == {1}
    assert x.d == x.h


def test_type_with_dict():
    """ Create a type with an explicit dictionary value
    that can hold any kv pairs
    """
    class X(NamedTuple):
        x: int
        y: Dict[str, Any]

    mk_x, serializer = p.type_constructor(X)

    with pytest.raises(colander.Invalid):
        mk_x({})

    with pytest.raises(colander.Invalid):
        mk_x({'x': 1})

    x = mk_x({'x': 1, 'y': {'x': 1}})
    assert x.x == x.y['x']


def test_type_with_unions():
    class VariantA(NamedTuple):
        variant_a: int

    class VariantB(NamedTuple):
        variant_b: int
        variant_b_attr: int

    class X(NamedTuple):
        x: Union[None, VariantA, VariantB]
        y: Union[str, VariantA]

    mk_x, dict_x = p.type_constructor(X)

    x = mk_x({'x': {'variant_a': 1}, 'y': 'y'})
    assert isinstance(x.x, VariantA)

    data = {'x': {'variant_b': 1, 'variant_b_attr': 1}, 'y': 'y'}
    x = mk_x(data)
    assert isinstance(x.x, VariantB)

    assert data == dict_x(x)

    assert mk_x({'x': None, 'y': 'y'}) == mk_x({'y': 'y'})
    with pytest.raises(colander.Invalid):
        # this is not the same as mk_x({}),
        # the empty structure is passed as attribute x,
        # which should match with only an empty named tuple definition,
        # which is not the same as None.
        mk_x({'x': {}})


def test_type_with_primitive_union():
    class X(NamedTuple):
        x: Union[None, str]

    mk_x, dict_x = p.type_constructor(X)

    x = mk_x({'x': None})
    assert x.x is None

    data = {'x': 'test'}
    x = mk_x(data)
    assert x.x == 'test'

    assert data == dict_x(x)


def test_union_primitive_match():
    class X(NamedTuple):
        # here, str() accepts everything that could be passed to int(),
        # and int() accepts everything that could be passed to float(),
        # and we still want to get int values instead of string values,
        # and float values instead of rounded int values.
        x: Union[str, int, float, bool]

    mk_x, serializer = p.type_constructor(X)

    x = mk_x({'x': 1})
    assert isinstance(x.x, int)

    x = mk_x({'x': 1.0})
    assert isinstance(x.x, float)

    if not p.PY36:
        # Python 3.6 has a bug that drops bool types from
        # unions that include int already, so
        # x: Union[int, bool] -- will be reduced to just `x: int`
        # x: Union[str, bool] -- will be left as is
        x = mk_x({'x': True})
        assert isinstance(x.x, bool)

    x = mk_x({'x': '1'})
    assert isinstance(x.x, str)


def test_parser_github_pull_request_payload():
    data = GITHUB_PR_PAYLOAD_JSON
    github_pr_dict = json.loads(data)
    parsed, overrides = cg.parse(github_pr_dict)
    typ, overrides_ = cg.construct_type('main', parsed)
    overrides.update(overrides_)

    python_source, __ = cg.codegen_py(typ, overrides)
    assert 'overrides' in python_source
    assert "PullRequest.links: '_links'," in python_source

    PullRequestType = get_type_hints(typ)['pull_request']

    assert PullRequestType.links in overrides
    assert overrides[PullRequestType.links] == '_links'

    constructor, serializer = p.type_constructor(
        typ,
        overrides=overrides
    )
    github_pr = constructor(github_pr_dict)
    assert github_pr.pull_request.links.comments.href.startswith('http')
    assert github_pr_dict == serializer(github_pr)


def test_extending():
    class X(NamedTuple):
        x: Money

    class MoneySchema(colander.Tuple):
        def deserialize(self, node, cstruct):
            r = super().deserialize(node, cstruct)
            if r in (colander.null, None):
                return r
            try:
                currency = Currency(r[0])
            except ValueError:
                raise colander.Invalid(node, f'Invalid currency token in {r}', cstruct)

            try:
                rv = Money(r[1], currency)
            except:
                raise colander.Invalid(node, f'Invalid amount in {r}', cstruct)

            return rv

        def serialize(self, node, appstruct: Optional[Money]):
            if appstruct is None or appstruct is colander.null:
                return appstruct

            r = (appstruct.currency, appstruct.amount)
            return super().serialize(node, r)

    schema_node = colander.SchemaNode(
        MoneySchema()
    )
    schema_node.children = [
        colander.SchemaNode(colander.Enum(Currency)),
        colander.SchemaNode(colander.Str()),
    ]
    mk_x, dict_x = p.type_constructor(X, {
        Money: p.TypeExtension(
            schema=schema_node
        )
    })

    serialized = {
        'x': ('GBP', '10')
    }

    x = mk_x(serialized)
    assert isinstance(x.x, Money)
    assert dict_x(x) == serialized



GITHUB_PR_PAYLOAD_JSON = """
{
  "action": "closed",
  "number": 1,
  "pull_request": {
    "url": "https://api.github.com/repos/Codertocat/Hello-World/pulls/1",
    "id": 191568743,
    "node_id": "MDExOlB1bGxSZXF1ZXN0MTkxNTY4NzQz",
    "html_url": "https://github.com/Codertocat/Hello-World/pull/1",
    "diff_url": "https://github.com/Codertocat/Hello-World/pull/1.diff",
    "patch_url": "https://github.com/Codertocat/Hello-World/pull/1.patch",
    "issue_url": "https://api.github.com/repos/Codertocat/Hello-World/issues/1",
    "number": 1,
    "state": "closed",
    "locked": false,
    "title": "Update the README with new information",
    "user": {
      "login": "Codertocat",
      "id": 21031067,
      "node_id": "MDQ6VXNlcjIxMDMxMDY3",
      "avatar_url": "https://avatars1.githubusercontent.com/u/21031067?v=4",
      "gravatar_id": "",
      "url": "https://api.github.com/users/Codertocat",
      "html_url": "https://github.com/Codertocat",
      "followers_url": "https://api.github.com/users/Codertocat/followers",
      "following_url": "https://api.github.com/users/Codertocat/following{/other_user}",
      "gists_url": "https://api.github.com/users/Codertocat/gists{/gist_id}",
      "starred_url": "https://api.github.com/users/Codertocat/starred{/owner}{/repo}",
      "subscriptions_url": "https://api.github.com/users/Codertocat/subscriptions",
      "organizations_url": "https://api.github.com/users/Codertocat/orgs",
      "repos_url": "https://api.github.com/users/Codertocat/repos",
      "events_url": "https://api.github.com/users/Codertocat/events{/privacy}",
      "received_events_url": "https://api.github.com/users/Codertocat/received_events",
      "type": "User",
      "site_admin": false
    },
    "body": "This is a pretty simple change that we need to pull into master.",
    "created_at": "2018-05-30T20:18:30Z",
    "updated_at": "2018-05-30T20:18:50Z",
    "closed_at": "2018-05-30T20:18:50Z",
    "merged_at": null,
    "merge_commit_sha": "414cb0069601a32b00bd122a2380cd283626a8e5",
    "assignee": null,
    "assignees": [
      "undefined"
    ],
    "requested_reviewers": [

    ],
    "requested_teams": [

    ],
    "labels": [

    ],
    "milestone": null,
    "commits_url": "https://api.github.com/repos/Codertocat/Hello-World/pulls/1/commits",
    "review_comments_url": "https://api.github.com/repos/Codertocat/Hello-World/pulls/1/comments",
    "review_comment_url": "https://api.github.com/repos/Codertocat/Hello-World/pulls/comments{/number}",
    "comments_url": "https://api.github.com/repos/Codertocat/Hello-World/issues/1/comments",
    "statuses_url": "https://api.github.com/repos/Codertocat/Hello-World/statuses/34c5c7793cb3b279e22454cb6750c80560547b3a",
    "head": {
      "label": "Codertocat:changes",
      "ref": "changes",
      "sha": "34c5c7793cb3b279e22454cb6750c80560547b3a",
      "user": {
        "login": "Codertocat",
        "id": 21031067,
        "node_id": "MDQ6VXNlcjIxMDMxMDY3",
        "avatar_url": "https://avatars1.githubusercontent.com/u/21031067?v=4",
        "gravatar_id": "",
        "url": "https://api.github.com/users/Codertocat",
        "html_url": "https://github.com/Codertocat",
        "followers_url": "https://api.github.com/users/Codertocat/followers",
        "following_url": "https://api.github.com/users/Codertocat/following{/other_user}",
        "gists_url": "https://api.github.com/users/Codertocat/gists{/gist_id}",
        "starred_url": "https://api.github.com/users/Codertocat/starred{/owner}{/repo}",
        "subscriptions_url": "https://api.github.com/users/Codertocat/subscriptions",
        "organizations_url": "https://api.github.com/users/Codertocat/orgs",
        "repos_url": "https://api.github.com/users/Codertocat/repos",
        "events_url": "https://api.github.com/users/Codertocat/events{/privacy}",
        "received_events_url": "https://api.github.com/users/Codertocat/received_events",
        "type": "User",
        "site_admin": false
      },
      "repo": {
        "id": 135493233,
        "node_id": "MDEwOlJlcG9zaXRvcnkxMzU0OTMyMzM=",
        "name": "Hello-World",
        "full_name": "Codertocat/Hello-World",
        "owner": {
          "login": "Codertocat",
          "id": 21031067,
          "node_id": "MDQ6VXNlcjIxMDMxMDY3",
          "avatar_url": "https://avatars1.githubusercontent.com/u/21031067?v=4",
          "gravatar_id": "",
          "url": "https://api.github.com/users/Codertocat",
          "html_url": "https://github.com/Codertocat",
          "followers_url": "https://api.github.com/users/Codertocat/followers",
          "following_url": "https://api.github.com/users/Codertocat/following{/other_user}",
          "gists_url": "https://api.github.com/users/Codertocat/gists{/gist_id}",
          "starred_url": "https://api.github.com/users/Codertocat/starred{/owner}{/repo}",
          "subscriptions_url": "https://api.github.com/users/Codertocat/subscriptions",
          "organizations_url": "https://api.github.com/users/Codertocat/orgs",
          "repos_url": "https://api.github.com/users/Codertocat/repos",
          "events_url": "https://api.github.com/users/Codertocat/events{/privacy}",
          "received_events_url": "https://api.github.com/users/Codertocat/received_events",
          "type": "User",
          "site_admin": false
        },
        "private": false,
        "html_url": "https://github.com/Codertocat/Hello-World",
        "description": null,
        "fork": false,
        "url": "https://api.github.com/repos/Codertocat/Hello-World",
        "forks_url": "https://api.github.com/repos/Codertocat/Hello-World/forks",
        "keys_url": "https://api.github.com/repos/Codertocat/Hello-World/keys{/key_id}",
        "collaborators_url": "https://api.github.com/repos/Codertocat/Hello-World/collaborators{/collaborator}",
        "teams_url": "https://api.github.com/repos/Codertocat/Hello-World/teams",
        "hooks_url": "https://api.github.com/repos/Codertocat/Hello-World/hooks",
        "issue_events_url": "https://api.github.com/repos/Codertocat/Hello-World/issues/events{/number}",
        "events_url": "https://api.github.com/repos/Codertocat/Hello-World/events",
        "assignees_url": "https://api.github.com/repos/Codertocat/Hello-World/assignees{/user}",
        "branches_url": "https://api.github.com/repos/Codertocat/Hello-World/branches{/branch}",
        "tags_url": "https://api.github.com/repos/Codertocat/Hello-World/tags",
        "blobs_url": "https://api.github.com/repos/Codertocat/Hello-World/git/blobs{/sha}",
        "git_tags_url": "https://api.github.com/repos/Codertocat/Hello-World/git/tags{/sha}",
        "git_refs_url": "https://api.github.com/repos/Codertocat/Hello-World/git/refs{/sha}",
        "trees_url": "https://api.github.com/repos/Codertocat/Hello-World/git/trees{/sha}",
        "statuses_url": "https://api.github.com/repos/Codertocat/Hello-World/statuses/{sha}",
        "languages_url": "https://api.github.com/repos/Codertocat/Hello-World/languages",
        "stargazers_url": "https://api.github.com/repos/Codertocat/Hello-World/stargazers",
        "contributors_url": "https://api.github.com/repos/Codertocat/Hello-World/contributors",
        "subscribers_url": "https://api.github.com/repos/Codertocat/Hello-World/subscribers",
        "subscription_url": "https://api.github.com/repos/Codertocat/Hello-World/subscription",
        "commits_url": "https://api.github.com/repos/Codertocat/Hello-World/commits{/sha}",
        "git_commits_url": "https://api.github.com/repos/Codertocat/Hello-World/git/commits{/sha}",
        "comments_url": "https://api.github.com/repos/Codertocat/Hello-World/comments{/number}",
        "issue_comment_url": "https://api.github.com/repos/Codertocat/Hello-World/issues/comments{/number}",
        "contents_url": "https://api.github.com/repos/Codertocat/Hello-World/contents/{+path}",
        "compare_url": "https://api.github.com/repos/Codertocat/Hello-World/compare/{base}...{head}",
        "merges_url": "https://api.github.com/repos/Codertocat/Hello-World/merges",
        "archive_url": "https://api.github.com/repos/Codertocat/Hello-World/{archive_format}{/ref}",
        "downloads_url": "https://api.github.com/repos/Codertocat/Hello-World/downloads",
        "issues_url": "https://api.github.com/repos/Codertocat/Hello-World/issues{/number}",
        "pulls_url": "https://api.github.com/repos/Codertocat/Hello-World/pulls{/number}",
        "milestones_url": "https://api.github.com/repos/Codertocat/Hello-World/milestones{/number}",
        "notifications_url": "https://api.github.com/repos/Codertocat/Hello-World/notifications{?since,all,participating}",
        "labels_url": "https://api.github.com/repos/Codertocat/Hello-World/labels{/name}",
        "releases_url": "https://api.github.com/repos/Codertocat/Hello-World/releases{/id}",
        "deployments_url": "https://api.github.com/repos/Codertocat/Hello-World/deployments",
        "created_at": "2018-05-30T20:18:04Z",
        "updated_at": "2018-05-30T20:18:50Z",
        "pushed_at": "2018-05-30T20:18:48Z",
        "git_url": "git://github.com/Codertocat/Hello-World.git",
        "ssh_url": "git@github.com:Codertocat/Hello-World.git",
        "clone_url": "https://github.com/Codertocat/Hello-World.git",
        "svn_url": "https://github.com/Codertocat/Hello-World",
        "homepage": null,
        "size": 0,
        "stargazers_count": 0,
        "watchers_count": 0,
        "language": null,
        "has_issues": true,
        "has_projects": true,
        "has_downloads": true,
        "has_wiki": true,
        "has_pages": true,
        "forks_count": 0,
        "mirror_url": null,
        "archived": false,
        "open_issues_count": 1,
        "license": null,
        "forks": 0,
        "open_issues": 1,
        "watchers": 0,
        "default_branch": "master"
      }
    },
    "base": {
      "label": "Codertocat:master",
      "ref": "master",
      "sha": "a10867b14bb761a232cd80139fbd4c0d33264240",
      "user": {
        "login": "Codertocat",
        "id": 21031067,
        "node_id": "MDQ6VXNlcjIxMDMxMDY3",
        "avatar_url": "https://avatars1.githubusercontent.com/u/21031067?v=4",
        "gravatar_id": "",
        "url": "https://api.github.com/users/Codertocat",
        "html_url": "https://github.com/Codertocat",
        "followers_url": "https://api.github.com/users/Codertocat/followers",
        "following_url": "https://api.github.com/users/Codertocat/following{/other_user}",
        "gists_url": "https://api.github.com/users/Codertocat/gists{/gist_id}",
        "starred_url": "https://api.github.com/users/Codertocat/starred{/owner}{/repo}",
        "subscriptions_url": "https://api.github.com/users/Codertocat/subscriptions",
        "organizations_url": "https://api.github.com/users/Codertocat/orgs",
        "repos_url": "https://api.github.com/users/Codertocat/repos",
        "events_url": "https://api.github.com/users/Codertocat/events{/privacy}",
        "received_events_url": "https://api.github.com/users/Codertocat/received_events",
        "type": "User",
        "site_admin": false
      },
      "repo": {
        "id": 135493233,
        "node_id": "MDEwOlJlcG9zaXRvcnkxMzU0OTMyMzM=",
        "name": "Hello-World",
        "full_name": "Codertocat/Hello-World",
        "owner": {
          "login": "Codertocat",
          "id": 21031067,
          "node_id": "MDQ6VXNlcjIxMDMxMDY3",
          "avatar_url": "https://avatars1.githubusercontent.com/u/21031067?v=4",
          "gravatar_id": "",
          "url": "https://api.github.com/users/Codertocat",
          "html_url": "https://github.com/Codertocat",
          "followers_url": "https://api.github.com/users/Codertocat/followers",
          "following_url": "https://api.github.com/users/Codertocat/following{/other_user}",
          "gists_url": "https://api.github.com/users/Codertocat/gists{/gist_id}",
          "starred_url": "https://api.github.com/users/Codertocat/starred{/owner}{/repo}",
          "subscriptions_url": "https://api.github.com/users/Codertocat/subscriptions",
          "organizations_url": "https://api.github.com/users/Codertocat/orgs",
          "repos_url": "https://api.github.com/users/Codertocat/repos",
          "events_url": "https://api.github.com/users/Codertocat/events{/privacy}",
          "received_events_url": "https://api.github.com/users/Codertocat/received_events",
          "type": "User",
          "site_admin": false
        },
        "private": false,
        "html_url": "https://github.com/Codertocat/Hello-World",
        "description": null,
        "fork": false,
        "url": "https://api.github.com/repos/Codertocat/Hello-World",
        "forks_url": "https://api.github.com/repos/Codertocat/Hello-World/forks",
        "keys_url": "https://api.github.com/repos/Codertocat/Hello-World/keys{/key_id}",
        "collaborators_url": "https://api.github.com/repos/Codertocat/Hello-World/collaborators{/collaborator}",
        "teams_url": "https://api.github.com/repos/Codertocat/Hello-World/teams",
        "hooks_url": "https://api.github.com/repos/Codertocat/Hello-World/hooks",
        "issue_events_url": "https://api.github.com/repos/Codertocat/Hello-World/issues/events{/number}",
        "events_url": "https://api.github.com/repos/Codertocat/Hello-World/events",
        "assignees_url": "https://api.github.com/repos/Codertocat/Hello-World/assignees{/user}",
        "branches_url": "https://api.github.com/repos/Codertocat/Hello-World/branches{/branch}",
        "tags_url": "https://api.github.com/repos/Codertocat/Hello-World/tags",
        "blobs_url": "https://api.github.com/repos/Codertocat/Hello-World/git/blobs{/sha}",
        "git_tags_url": "https://api.github.com/repos/Codertocat/Hello-World/git/tags{/sha}",
        "git_refs_url": "https://api.github.com/repos/Codertocat/Hello-World/git/refs{/sha}",
        "trees_url": "https://api.github.com/repos/Codertocat/Hello-World/git/trees{/sha}",
        "statuses_url": "https://api.github.com/repos/Codertocat/Hello-World/statuses/{sha}",
        "languages_url": "https://api.github.com/repos/Codertocat/Hello-World/languages",
        "stargazers_url": "https://api.github.com/repos/Codertocat/Hello-World/stargazers",
        "contributors_url": "https://api.github.com/repos/Codertocat/Hello-World/contributors",
        "subscribers_url": "https://api.github.com/repos/Codertocat/Hello-World/subscribers",
        "subscription_url": "https://api.github.com/repos/Codertocat/Hello-World/subscription",
        "commits_url": "https://api.github.com/repos/Codertocat/Hello-World/commits{/sha}",
        "git_commits_url": "https://api.github.com/repos/Codertocat/Hello-World/git/commits{/sha}",
        "comments_url": "https://api.github.com/repos/Codertocat/Hello-World/comments{/number}",
        "issue_comment_url": "https://api.github.com/repos/Codertocat/Hello-World/issues/comments{/number}",
        "contents_url": "https://api.github.com/repos/Codertocat/Hello-World/contents/{+path}",
        "compare_url": "https://api.github.com/repos/Codertocat/Hello-World/compare/{base}...{head}",
        "merges_url": "https://api.github.com/repos/Codertocat/Hello-World/merges",
        "archive_url": "https://api.github.com/repos/Codertocat/Hello-World/{archive_format}{/ref}",
        "downloads_url": "https://api.github.com/repos/Codertocat/Hello-World/downloads",
        "issues_url": "https://api.github.com/repos/Codertocat/Hello-World/issues{/number}",
        "pulls_url": "https://api.github.com/repos/Codertocat/Hello-World/pulls{/number}",
        "milestones_url": "https://api.github.com/repos/Codertocat/Hello-World/milestones{/number}",
        "notifications_url": "https://api.github.com/repos/Codertocat/Hello-World/notifications{?since,all,participating}",
        "labels_url": "https://api.github.com/repos/Codertocat/Hello-World/labels{/name}",
        "releases_url": "https://api.github.com/repos/Codertocat/Hello-World/releases{/id}",
        "deployments_url": "https://api.github.com/repos/Codertocat/Hello-World/deployments",
        "created_at": "2018-05-30T20:18:04Z",
        "updated_at": "2018-05-30T20:18:50Z",
        "pushed_at": "2018-05-30T20:18:48Z",
        "git_url": "git://github.com/Codertocat/Hello-World.git",
        "ssh_url": "git@github.com:Codertocat/Hello-World.git",
        "clone_url": "https://github.com/Codertocat/Hello-World.git",
        "svn_url": "https://github.com/Codertocat/Hello-World",
        "homepage": null,
        "size": 0,
        "stargazers_count": 0,
        "watchers_count": 0,
        "language": null,
        "has_issues": true,
        "has_projects": true,
        "has_downloads": true,
        "has_wiki": true,
        "has_pages": true,
        "forks_count": 0,
        "mirror_url": null,
        "archived": false,
        "open_issues_count": 1,
        "license": null,
        "forks": 0,
        "open_issues": 1,
        "watchers": 0,
        "default_branch": "master"
      }
    },
    "_links": {
      "self": {
        "href": "https://api.github.com/repos/Codertocat/Hello-World/pulls/1"
      },
      "html": {
        "href": "https://github.com/Codertocat/Hello-World/pull/1"
      },
      "issue": {
        "href": "https://api.github.com/repos/Codertocat/Hello-World/issues/1"
      },
      "comments": {
        "href": "https://api.github.com/repos/Codertocat/Hello-World/issues/1/comments"
      },
      "review_comments": {
        "href": "https://api.github.com/repos/Codertocat/Hello-World/pulls/1/comments"
      },
      "review_comment": {
        "href": "https://api.github.com/repos/Codertocat/Hello-World/pulls/comments{/number}"
      },
      "commits": {
        "href": "https://api.github.com/repos/Codertocat/Hello-World/pulls/1/commits"
      },
      "statuses": {
        "href": "https://api.github.com/repos/Codertocat/Hello-World/statuses/34c5c7793cb3b279e22454cb6750c80560547b3a"
      }
    },
    "author_association": "OWNER",
    "merged": false,
    "mergeable": true,
    "rebaseable": true,
    "mergeable_state": "clean",
    "merged_by": null,
    "comments": 0,
    "review_comments": 1,
    "maintainer_can_modify": false,
    "commits": 1,
    "additions": 1,
    "deletions": 1,
    "changed_files": 1
  },
  "repository": {
    "id": 135493233,
    "node_id": "MDEwOlJlcG9zaXRvcnkxMzU0OTMyMzM=",
    "name": "Hello-World",
    "full_name": "Codertocat/Hello-World",
    "owner": {
      "login": "Codertocat",
      "id": 21031067,
      "node_id": "MDQ6VXNlcjIxMDMxMDY3",
      "avatar_url": "https://avatars1.githubusercontent.com/u/21031067?v=4",
      "gravatar_id": "",
      "url": "https://api.github.com/users/Codertocat",
      "html_url": "https://github.com/Codertocat",
      "followers_url": "https://api.github.com/users/Codertocat/followers",
      "following_url": "https://api.github.com/users/Codertocat/following{/other_user}",
      "gists_url": "https://api.github.com/users/Codertocat/gists{/gist_id}",
      "starred_url": "https://api.github.com/users/Codertocat/starred{/owner}{/repo}",
      "subscriptions_url": "https://api.github.com/users/Codertocat/subscriptions",
      "organizations_url": "https://api.github.com/users/Codertocat/orgs",
      "repos_url": "https://api.github.com/users/Codertocat/repos",
      "events_url": "https://api.github.com/users/Codertocat/events{/privacy}",
      "received_events_url": "https://api.github.com/users/Codertocat/received_events",
      "type": "User",
      "site_admin": false
    },
    "private": false,
    "html_url": "https://github.com/Codertocat/Hello-World",
    "description": null,
    "fork": false,
    "url": "https://api.github.com/repos/Codertocat/Hello-World",
    "forks_url": "https://api.github.com/repos/Codertocat/Hello-World/forks",
    "keys_url": "https://api.github.com/repos/Codertocat/Hello-World/keys{/key_id}",
    "collaborators_url": "https://api.github.com/repos/Codertocat/Hello-World/collaborators{/collaborator}",
    "teams_url": "https://api.github.com/repos/Codertocat/Hello-World/teams",
    "hooks_url": "https://api.github.com/repos/Codertocat/Hello-World/hooks",
    "issue_events_url": "https://api.github.com/repos/Codertocat/Hello-World/issues/events{/number}",
    "events_url": "https://api.github.com/repos/Codertocat/Hello-World/events",
    "assignees_url": "https://api.github.com/repos/Codertocat/Hello-World/assignees{/user}",
    "branches_url": "https://api.github.com/repos/Codertocat/Hello-World/branches{/branch}",
    "tags_url": "https://api.github.com/repos/Codertocat/Hello-World/tags",
    "blobs_url": "https://api.github.com/repos/Codertocat/Hello-World/git/blobs{/sha}",
    "git_tags_url": "https://api.github.com/repos/Codertocat/Hello-World/git/tags{/sha}",
    "git_refs_url": "https://api.github.com/repos/Codertocat/Hello-World/git/refs{/sha}",
    "trees_url": "https://api.github.com/repos/Codertocat/Hello-World/git/trees{/sha}",
    "statuses_url": "https://api.github.com/repos/Codertocat/Hello-World/statuses/{sha}",
    "languages_url": "https://api.github.com/repos/Codertocat/Hello-World/languages",
    "stargazers_url": "https://api.github.com/repos/Codertocat/Hello-World/stargazers",
    "contributors_url": "https://api.github.com/repos/Codertocat/Hello-World/contributors",
    "subscribers_url": "https://api.github.com/repos/Codertocat/Hello-World/subscribers",
    "subscription_url": "https://api.github.com/repos/Codertocat/Hello-World/subscription",
    "commits_url": "https://api.github.com/repos/Codertocat/Hello-World/commits{/sha}",
    "git_commits_url": "https://api.github.com/repos/Codertocat/Hello-World/git/commits{/sha}",
    "comments_url": "https://api.github.com/repos/Codertocat/Hello-World/comments{/number}",
    "issue_comment_url": "https://api.github.com/repos/Codertocat/Hello-World/issues/comments{/number}",
    "contents_url": "https://api.github.com/repos/Codertocat/Hello-World/contents/{+path}",
    "compare_url": "https://api.github.com/repos/Codertocat/Hello-World/compare/{base}...{head}",
    "merges_url": "https://api.github.com/repos/Codertocat/Hello-World/merges",
    "archive_url": "https://api.github.com/repos/Codertocat/Hello-World/{archive_format}{/ref}",
    "downloads_url": "https://api.github.com/repos/Codertocat/Hello-World/downloads",
    "issues_url": "https://api.github.com/repos/Codertocat/Hello-World/issues{/number}",
    "pulls_url": "https://api.github.com/repos/Codertocat/Hello-World/pulls{/number}",
    "milestones_url": "https://api.github.com/repos/Codertocat/Hello-World/milestones{/number}",
    "notifications_url": "https://api.github.com/repos/Codertocat/Hello-World/notifications{?since,all,participating}",
    "labels_url": "https://api.github.com/repos/Codertocat/Hello-World/labels{/name}",
    "releases_url": "https://api.github.com/repos/Codertocat/Hello-World/releases{/id}",
    "deployments_url": "https://api.github.com/repos/Codertocat/Hello-World/deployments",
    "created_at": "2018-05-30T20:18:04Z",
    "updated_at": "2018-05-30T20:18:50Z",
    "pushed_at": "2018-05-30T20:18:48Z",
    "git_url": "git://github.com/Codertocat/Hello-World.git",
    "ssh_url": "git@github.com:Codertocat/Hello-World.git",
    "clone_url": "https://github.com/Codertocat/Hello-World.git",
    "svn_url": "https://github.com/Codertocat/Hello-World",
    "homepage": null,
    "size": 0,
    "stargazers_count": 0,
    "watchers_count": 0,
    "language": null,
    "has_issues": true,
    "has_projects": true,
    "has_downloads": true,
    "has_wiki": true,
    "has_pages": true,
    "forks_count": 0,
    "mirror_url": null,
    "archived": false,
    "open_issues_count": 1,
    "license": null,
    "forks": 0,
    "open_issues": 1,
    "watchers": 0,
    "default_branch": "master"
  },
  "sender": {
    "login": "Codertocat",
    "id": 21031067,
    "node_id": "MDQ6VXNlcjIxMDMxMDY3",
    "avatar_url": "https://avatars1.githubusercontent.com/u/21031067?v=4",
    "gravatar_id": "",
    "url": "https://api.github.com/users/Codertocat",
    "html_url": "https://github.com/Codertocat",
    "followers_url": "https://api.github.com/users/Codertocat/followers",
    "following_url": "https://api.github.com/users/Codertocat/following{/other_user}",
    "gists_url": "https://api.github.com/users/Codertocat/gists{/gist_id}",
    "starred_url": "https://api.github.com/users/Codertocat/starred{/owner}{/repo}",
    "subscriptions_url": "https://api.github.com/users/Codertocat/subscriptions",
    "organizations_url": "https://api.github.com/users/Codertocat/orgs",
    "repos_url": "https://api.github.com/users/Codertocat/repos",
    "events_url": "https://api.github.com/users/Codertocat/events{/privacy}",
    "received_events_url": "https://api.github.com/users/Codertocat/received_events",
    "type": "User",
    "site_admin": false
  }
}
"""