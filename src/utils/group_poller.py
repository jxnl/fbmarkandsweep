import facebook
import requests
import datetime
from datetime import timedelta
import dateutil.parser

access_token = "CAAK5npFF7MYBACPwdYQRuqHwmQj18YsRDdkUiU1WfyHvs2a5AaNzyNihyqXg18UdGTyaJi9pWReXGQmJZAMtDpvOM8jqQ6c1GuvQLdKqLjvTHhyBIsYU26iLcLgUZAj4e9hnV9iyZAjwi4tr2gk5TAcNNJ71Nyctmzro1GFaikZCfVaoB42BS6AtEY6ypFZAxf6wpGUSYAjD3TMusTUeA"

class GroupPoller:
    def __init__(self, access_token, group_id):
        self.access_token = str(access_token)
        self.group_id = str(group_id)

        self.graph = facebook.GraphAPI(self.access_token)

    def paginate_top(self):
        posts = self.graph.get_connections(self.group_id, "feed")
        self.all_posts = (FacebookPost(post) for post in posts['data'])

        #for post in all_posts:
        #    print post.post_id + "||" + post.contents.replace("\n", " ")

    def paginate_all(self, max_results=100, last_tick=0):
        all_posts = list()
        posts = self.graph.get_connections(self.group_id, "feed")

        while True:
            # This will evaluate to false when there is no data
            if 'paging' in posts:
                for post in posts['data']:
                    fb_post = FacebookPost(post)
                    if fb_post:
                        # Stop returning an infinite result after the max_results is reached
                        if len(all_posts) > max_results - 1:
                            return all_posts
                        else:
                            # If the time that the post was created was /earlier/ then the last thing we've seen
                            # discard it and return what we have.
                            if fb_post.created_at < last_tick:
                                return all_posts
                            # Otherwise, we should know about it because it was created within the time that we
                            # last checked things out, so we should add it and then keep going
                            else:
                                all_posts.append(fb_post)

                posts = requests.get(posts['paging']['next']).json()
            else:
                break

        return all_posts

class FacebookPost:
    def __init__(self, post):
        self.created_at = dateutil.parser.parse(post['created_time']).replace(tzinfo=None)

        self.group_id = post['id'].split("_")[0]
        self.post_id = post['id'].split("_")[1]

        self.poster = post['from']

        # Not all posts have messages, apparently!
        try:
            self.contents = post['message']
        except KeyError:
            self.contents = ""

        self.comments = list()

        # Some posts also don't have any comments
        if 'comments' in post:
            for comment in post['comments']['data']:
                self.comments.append(FacebookComment(self, comment))

    def post_comment(self, body):
        r = requests.post('https://graph.facebook.com/v2.1/' + self.post_id + '/comments?access_token=' + access_token + '&message=' + body)
        return r.json()

    def delete_post(self, body):
        r = requests.delete('https://graph.facebook.com/v2.1/' + self.post_id + '?access_token=' + access_token)
        return r.json()


class FacebookComment:
    def __init__(self, parent_post, comment_raw):
        self.parent_post = parent_post

        self.poster = comment_raw['from']
        self.contents = comment_raw['message']
        self.like_count = comment_raw['like_count']

    def post_comment(self, body):
        self.parent_post.post_comment(body)
