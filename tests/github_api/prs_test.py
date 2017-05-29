import unittest

from unittest.mock import Mock, call

from github_api import prs, API


class TestPRMethods(unittest.TestCase):
    def test_statuses_returns_passed_travis_build_on_page_1_of_1(self):
        pr = "/repos/test/blah"
        json_response = [{"state": "failure",
                          "context": "chaosbot"},
                         {"state": "pending",
                          "context": "chaosbot"},
                         {"state": "success",
                          "context": prs.TRAVIS_CI_CONTEXT}
                         ]
        headers_response = {"X-GitHub-Media-Type": "github.v3; format=json"}

        api = API("user", "pat")
        api.call_with_headers = Mock()
        api.call_with_headers.side_effect = [(json_response, headers_response)]
        url = "{}{}".format(api.BASE_URL, pr)

        self.assertTrue(prs.has_build_passed(api, url))

        calls = [call('get', '/repos/test/blah')]
        api.call_with_headers.assert_has_calls(calls)
        self.assertEqual(1, api.call_with_headers.call_count)

    def test_statuses_returns_passed_travis_build_on_success_page_3_of_4(self):
        pr = "/repos/user/repo"
        json_response = [[{"state": "failure",  # page 1
                           "context": "chaosbot"},
                          {"state": "pending",
                           "context": "chaosbot"},
                          ],
                         [{"state": "failure",  # page 2
                           "context": "chaosbot"},
                          {"state": "pending",
                           "context": "chaosbot"},
                          ],
                         [{"state": "failure",  # page 3
                           "context": "chaosbot"},
                          {"state": "success",
                           "context": prs.TRAVIS_CI_CONTEXT},
                          ],
                         [{"state": "failure",  # page 4
                           "context": "chaosbot"},
                          {"state": "pending",
                           "context": "chaosbot"},
                          ]]
        headers_response = [{"X-GitHub-Media-Type": "github.v3; format=json",  # page 1
                             "Link": '<https://api.github.com/repositories/repo/statuses/'
                                     'sha?page=2>; rel="next", <https://api.github.com/re'
                                     'positories/repo/statuses/sha?page=4>; rel="last"'},
                            {"X-GitHub-Media-Type": "github.v3; format=json",  # page 2
                             "Link": '<https://api.github.com/repositories/repo/statuses/s'
                                     'ha?page=3>; rel="next", <https://api.github.com/repo'
                                     'sitories/repo/statuses/sha?page=4>; rel="last", <htt'
                                     'ps://api.github.com/repositories/repo/statuses/sha?p'
                                     'age=1>; rel="first", <https://api.github.com/reposit'
                                     'ories/repo/statuses/sha?page=1>; rel="prev"'},
                            {"X-GitHub-Media-Type": "github.v3; format=json",  # page 3
                             "Link": '<https://api.github.com/repositories/repo/statuses/s'
                                     'ha?page=4>; rel="next", <https://api.github.com/repo'
                                     'sitories/repo/statuses/sha?page=4>; rel="last", <htt'
                                     'ps://api.github.com/repositories/repo/statuses/sha?p'
                                     'age=1>; rel="first", <https://api.github.com/reposit'
                                     'ories/repo/statuses/sha?page=2>; rel="prev"'},
                            {"X-GitHub-Media-Type": "github.v3; format=json",  # page 4
                             "Link": '<https://api.github.com/repositories/repo/statuses/s'
                                     'ha?page=1>; rel="first", <https://api.github.com/rep'
                                     'ositories/repo/statuses/sha?page=3>; rel="prev"'},
                            ]
        api = API("user", "pat")
        api.call_with_headers = Mock()
        api.call_with_headers.side_effect = [(json_response[i], headers_response[i])
                                             for i in range(4)]
        url = "{}{}".format(api.BASE_URL, pr)
        self.assertTrue(prs.has_build_passed(api, url))

        calls = [call('get', '/repos/user/repo'),
                 call('get', '/repositories/repo/statuses/sha?page=2'),
                 call('get', '/repositories/repo/statuses/sha?page=3')]
        api.call_with_headers.assert_has_calls(calls)
        self.assertEqual(3, api.call_with_headers.call_count)

    def test_statuses_returns_failed_travis_build_on_pending_page_4_of_4(self):
        pr = "/repos/user/repo"
        json_response = [[{"state": "failure",  # page 1
                           "context": "chaosbot"},
                          {"state": "pending",
                           "context": "chaosbot"},
                          ],
                         [{"state": "failure",  # page 2
                           "context": "chaosbot"},
                          {"state": "pending",
                           "context": "chaosbot"},
                          ],
                         [{"state": "failure",  # page 3
                           "context": "chaosbot"},
                          {"state": "success",
                           "context": "some_context"},
                          ],
                         [{"state": "failure",  # page 4
                           "context": "chaosbot"},
                          {"state": "pending",
                           "context": prs.TRAVIS_CI_CONTEXT},
                          ]]
        headers_response = [{"X-GitHub-Media-Type": "github.v3; format=json",  # page 1
                             "Link": '<https://api.github.com/repositories/repo/statuses/'
                                     'sha?page=2>; rel="next", <https://api.github.com/re'
                                     'positories/repo/statuses/sha?page=4>; rel="last"'},
                            {"X-GitHub-Media-Type": "github.v3; format=json",  # page 2
                             "Link": '<https://api.github.com/repositories/repo/statuses/s'
                                     'ha?page=3>; rel="next", <https://api.github.com/repo'
                                     'sitories/repo/statuses/sha?page=4>; rel="last", <htt'
                                     'ps://api.github.com/repositories/repo/statuses/sha?p'
                                     'age=1>; rel="first", <https://api.github.com/reposit'
                                     'ories/repo/statuses/sha?page=1>; rel="prev"'},
                            {"X-GitHub-Media-Type": "github.v3; format=json",  # page 3
                             "Link": '<https://api.github.com/repositories/repo/statuses/s'
                                     'ha?page=4>; rel="next", <https://api.github.com/repo'
                                     'sitories/repo/statuses/sha?page=4>; rel="last", <htt'
                                     'ps://api.github.com/repositories/repo/statuses/sha?p'
                                     'age=1>; rel="first", <https://api.github.com/reposit'
                                     'ories/repo/statuses/sha?page=2>; rel="prev"'},
                            {"X-GitHub-Media-Type": "github.v3; format=json",  # page 4
                             "Link": '<https://api.github.com/repositories/repo/statuses/s'
                                     'ha?page=1>; rel="first", <https://api.github.com/rep'
                                     'ositories/repo/statuses/sha?page=3>; rel="prev"'},
                            ]
        api = API("user", "pat")
        api.call_with_headers = Mock()
        api.call_with_headers.side_effect = [(json_response[i], headers_response[i])
                                             for i in range(4)]
        url = "{}{}".format(api.BASE_URL, pr)
        self.assertFalse(prs.has_build_passed(api, url))

        calls = [call('get', '/repos/user/repo'),
                 call('get', '/repositories/repo/statuses/sha?page=2'),
                 call('get', '/repositories/repo/statuses/sha?page=3'),
                 call('get', '/repositories/repo/statuses/sha?page=4')]
        api.call_with_headers.assert_has_calls(calls)
        self.assertEqual(4, api.call_with_headers.call_count)

    def test_statuses_returns_failed_travis_build_on_failed_page_1_of_3(self):
        pr = "/repos/user/repo"
        json_response = [[{"state": "failure",  # page 1
                           "context": prs.TRAVIS_CI_CONTEXT},
                          {"state": "pending",
                           "context": "chaosbot"},
                          ],
                         [{"state": "failure",  # page 2
                           "context": "chaosbot"},
                          {"state": "pending",
                           "context": "chaosbot"},
                          ],
                         [{"state": "failure",  # page 3
                           "context": "choasbot"},
                          {"state": "success",
                           "context": "some_context"},
                          ]]
        headers_response = [{"X-GitHub-Media-Type": "github.v3; format=json",  # page 1
                             "Link": '<https://api.github.com/repositories/repo/statuses/'
                                     'sha?page=2>; rel="next", <https://api.github.com/re'
                                     'positories/repo/statuses/sha?page=3>; rel="last"'},
                            {"X-GitHub-Media-Type": "github.v3; format=json",  # page 2
                             "Link": '<https://api.github.com/repositories/repo/statuses/s'
                                     'ha?page=3>; rel="next", <https://api.github.com/repo'
                                     'sitories/repo/statuses/sha?page=3>; rel="last", <htt'
                                     'ps://api.github.com/repositories/repo/statuses/sha?p'
                                     'age=1>; rel="first", <https://api.github.com/reposit'
                                     'ories/repo/statuses/sha?page=1>; rel="prev"'},
                            {"X-GitHub-Media-Type": "github.v3; format=json",  # page 3
                             "Link": '<https://api.github.com/repositories/repo/statuses/sha?p'
                                     'age=1>; rel="first", <https://api.github.com/reposit'
                                     'ories/repo/statuses/sha?page=2>; rel="prev"'}
                            ]
        api = API("user", "pat")
        api.call_with_headers = Mock()
        api.call_with_headers.side_effect = [(json_response[i], headers_response[i])
                                             for i in range(3)]
        url = "{}{}".format(api.BASE_URL, pr)
        self.assertFalse(prs.has_build_passed(api, url))

        calls = [call('get', '/repos/user/repo')]
        api.call_with_headers.assert_has_calls(calls)
        self.assertEqual(1, api.call_with_headers.call_count)

    def test_statuses_returns_passed_travis_build_on_no_ci_page_3_of_3(self):
        pr = "/repos/user/repo"
        json_response = [[{"state": "failure",  # page 1
                           "context": "not_travis"},
                          {"state": "pending",
                           "context": "chaosbot"},
                          ],
                         [{"state": "failure",  # page 2
                           "context": "chaosbot"},
                          {"state": "pending",
                           "context": "chaosbot"},
                          ],
                         [{"state": "failure",  # page 3
                           "context": "choasbot"},
                          {"state": "success",
                           "context": "some_context"},
                          ]]
        headers_response = [{"X-GitHub-Media-Type": "github.v3; format=json",  # page 1
                             "Link": '<https://api.github.com/repositories/repo/statuses/'
                                     'sha?page=2>; rel="next", <https://api.github.com/re'
                                     'positories/repo/statuses/sha?page=3>; rel="last"'},
                            {"X-GitHub-Media-Type": "github.v3; format=json",  # page 2
                             "Link": '<https://api.github.com/repositories/repo/statuses/s'
                                     'ha?page=3>; rel="next", <https://api.github.com/repo'
                                     'sitories/repo/statuses/sha?page=3>; rel="last", <htt'
                                     'ps://api.github.com/repositories/repo/statuses/sha?p'
                                     'age=1>; rel="first", <https://api.github.com/reposit'
                                     'ories/repo/statuses/sha?page=1>; rel="prev"'},
                            {"X-GitHub-Media-Type": "github.v3; format=json",  # page 3
                             "Link": '<https://api.github.com/repositories/repo/statuses/sha?p'
                                     'age=1>; rel="first", <https://api.github.com/reposit'
                                     'ories/repo/statuses/sha?page=2>; rel="prev"'}
                            ]
        api = API("user", "pat")
        api.call_with_headers = Mock()
        api.call_with_headers.side_effect = [(json_response[i], headers_response[i])
                                             for i in range(3)]
        url = "{}{}".format(api.BASE_URL, pr)
        self.assertTrue(prs.has_build_passed(api, url))

        calls = [call('get', '/repos/user/repo'),
                 call('get', '/repositories/repo/statuses/sha?page=2'),
                 call('get', '/repositories/repo/statuses/sha?page=3')]
        api.call_with_headers.assert_has_calls(calls)
        self.assertEqual(3, api.call_with_headers.call_count)

    def test_statuses_returns_passed_when_no_status_url(self):
        self.assertTrue(prs.has_build_passed(None, None))
        self.assertTrue(prs.has_build_passed(None, ""))
