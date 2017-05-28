import arrow
import math
import settings
from requests import HTTPError
from . import misc
from . import voting
from . import comments
from . import exceptions as exc


def merge_pr(api, urn, pr, votes, total, threshold):
    """ merge a pull request, if possible, and use a nice detailed merge commit
    message """

    pr_num = pr["number"]
    pr_title = pr['title']
    pr_description = pr['body']

    path = "/repos/{urn}/pulls/{pr}/merge".format(urn=urn, pr=pr_num)

    record = voting.friendly_voting_record(votes)
    if record:
        record = "Vote record:\n" + record

    votes_summary = formatted_votes_summary(votes, total, threshold)

    pr_url = "https://github.com/{urn}/pull/{pr}".format(urn=urn, pr=pr_num)

    title = "merging PR #{num}: {pr_title}".format(
        num=pr_num, pr_title=pr_title)
    desc = """
{pr_url}: {pr_title}

Description:
{pr_description}

:ok_woman: PR passed {summary}.

{record}
""".strip().format(
        pr_url=pr_url,
        pr_title=pr_title,
        pr_description=pr_description,
        summary=votes_summary,
        record=record,
    )

    data = {
        "commit_title": title,
        "commit_message": desc,
        "merge_method": "merge",

        # if some clever person attempts to submit more commits while we're
        # aggregating votes, this sha check will fail and no merge will occur
        "sha": pr["head"]["sha"],
    }
    try:
        resp = api("PUT", path, json=data)
        return resp["sha"]
    except HTTPError as e:
        resp = e.response
        # could not be merged
        if resp.status_code == 405:
            raise exc.CouldntMerge
        # someone trying to be sneaky and change their PR commits during voting
        elif resp.status_code == 409:
            raise exc.CouldntMerge
        else:
            raise


def formatted_votes_summary(votes, total, threshold):
    vfor = sum(v for v in votes.values() if v > 0)
    vagainst = abs(sum(v for v in votes.values() if v < 0))

    return ("with a vote of {vfor} for and {vagainst} against, with a weighted total \
            of {total:.1f} and a threshold of {threshold:.1f}"
            .strip().format(vfor=vfor, vagainst=vagainst, total=total, threshold=threshold))


def formatted_votes_short_summary(votes, total, threshold):
    vfor = sum(v for v in votes.values() if v > 0)
    vagainst = abs(sum(v for v in votes.values() if v < 0))

    return "vote: {vfor}-{vagainst}, weighted total: {total:.1f}, threshold: {threshold:.1f}" \
        .strip().format(vfor=vfor, vagainst=vagainst, total=total, threshold=threshold)


def label_pr(api, urn, pr_num, labels):
    """ set a pr's labels (removes old labels) """
    if not isinstance(labels, (tuple, list)):
        labels = [labels]
    path = "/repos/{urn}/issues/{pr}/labels".format(urn=urn, pr=pr_num)
    data = labels
    return api("PUT", path, json=data)


def close_pr(api, urn, pr):
    """ https://developer.github.com/v3/pulls/#update-a-pull-request """
    path = "/repos/{urn}/pulls/{pr}".format(urn=urn, pr=pr["number"])
    data = {
        "state": "closed",
    }
    return api("patch", path, json=data)


def get_pr_last_updated(pr_data):
    """ a helper for finding the utc datetime of the last pr branch
    modifications """
    repo = pr_data["head"]["repo"]
    if repo:
        return arrow.get(repo["pushed_at"])
    else:
        return None


def get_pr_comments(api, urn, pr_num):
    """ yield all comments on a pr, weirdly excluding the initial pr comment
    itself (the one the owner makes) """
    params = {
        "per_page": settings.DEFAULT_PAGINATION
    }
    path = "/repos/{urn}/issues/{pr}/comments".format(urn=urn, pr=pr_num)
    comments = api("get", path, params=params)
    for comment in comments:
        yield comment


def get_ready_prs(api, urn, window):
    """ yield mergeable, non-WIP prs that have had no modifications for longer
    than the voting window.  these are prs that are ready to be considered for
    merging """
    open_prs = get_open_prs(api, urn)
    for pr in open_prs:
        pr_num = pr["number"]

        now = arrow.utcnow()
        updated = get_pr_last_updated(pr)
        if updated is None:
            comments.leave_deleted_comment(api, urn, pr["number"])
            close_pr(api, urn, pr)
            continue

        delta = (now - updated).total_seconds()

        is_wip = "WIP" in pr["title"]

        if not is_wip and delta > window:
            # we check if its mergeable if its outside the voting window,
            # because there seems to be a race where a freshly-created PR exists
            # in the paginated list of PRs, but 404s when trying to fetch it
            # directly
            mergeable = get_is_mergeable(api, urn, pr_num)
            if mergeable is True:
                label_pr(api, urn, pr_num, [])
                yield pr
            elif mergeable is False:
                label_pr(api, urn, pr_num, ["conflicts"])
                if delta >= 60 * 60 * settings.PR_STALE_HOURS:
                    comments.leave_stale_comment(
                        api, urn, pr["number"], round(delta / 60 / 60))
                    close_pr(api, urn, pr)
            # mergeable can also be None, in which case we just skip it for now


def voting_window_remaining_seconds(pr, window):
    now = arrow.utcnow()
    updated = get_pr_last_updated(pr)
    if updated is None:
        return math.inf
    delta = (now - updated).total_seconds()
    return window - delta


def is_pr_in_voting_window(pr, window):
    return voting_window_remaining_seconds(pr, window) <= 0


def get_pr_reviews(api, urn, pr_num):
    """ get all pr reviews on a pr
    https://help.github.com/articles/about-pull-request-reviews/ """
    params = {
        "per_page": settings.DEFAULT_PAGINATION
    }
    path = "/repos/{urn}/pulls/{pr}/reviews".format(urn=urn, pr=pr_num)
    data = api("get", path, params=params)
    return data


def get_is_mergeable(api, urn, pr_num):
    return get_pr(api, urn, pr_num)["mergeable"]


def get_pr(api, urn, pr_num):
    """ helper for fetching a pr.  necessary because the "mergeable" field does
    not exist on prs that come back from paginated endpoints, so we must fetch
    the pr directly """
    path = "/repos/{urn}/pulls/{pr}".format(urn=urn, pr=pr_num)
    pr = api("get", path)
    return pr


def get_open_prs(api, urn):
    params = {
        "state": "open",
        "sort": "updated",
        "direction": "asc",
        "per_page": settings.DEFAULT_PAGINATION,
    }
    path = "/repos/{urn}/pulls".format(urn=urn)
    data = api("get", path, params=params)
    return data


def get_reactions_for_pr(api, urn, pr):
    path = "/repos/{urn}/issues/{pr}/reactions".format(urn=urn, pr=pr)
    params = {"per_page": settings.DEFAULT_PAGINATION}
    reactions = api("get", path, params=params)
    for reaction in reactions:
        yield reaction


def post_accepted_status(api, urn, pr, voting_window, votes, total, threshold):
    sha = pr["head"]["sha"]

    remaining_seconds = voting_window_remaining_seconds(pr, voting_window)
    remaining_human = misc.seconds_to_human(remaining_seconds)
    votes_summary = formatted_votes_short_summary(votes, total, threshold)

    post_status(api, urn, sha, "success",
                "remaining: {time}, {summary}".format(time=remaining_human, summary=votes_summary))


def post_rejected_status(api, urn, pr, voting_window, votes, total, threshold):
    sha = pr["head"]["sha"]

    remaining_seconds = voting_window_remaining_seconds(pr, voting_window)
    remaining_human = misc.seconds_to_human(remaining_seconds)
    votes_summary = formatted_votes_short_summary(votes, total, threshold)

    post_status(api, urn, sha, "failure",
                "remaining: {time}, {summary}".format(time=remaining_human, summary=votes_summary))


def post_pending_status(api, urn, pr, voting_window, votes, total, threshold):
    sha = pr["head"]["sha"]

    remaining_seconds = voting_window_remaining_seconds(pr, voting_window)
    remaining_human = misc.seconds_to_human(remaining_seconds)
    votes_summary = formatted_votes_short_summary(votes, total, threshold)

    post_status(api, urn, sha, "pending",
                "remaining: {time}, {summary}".format(time=remaining_human, summary=votes_summary))


def post_status(api, urn, sha, state, description):
    """ apply an issue label to a pr """
    path = "/repos/{urn}/statuses/{sha}".format(urn=urn, sha=sha)
    data = {
        "state": state,
        "description": description,
        "context": "chaosbot"
    }
    api("POST", path, json=data)
