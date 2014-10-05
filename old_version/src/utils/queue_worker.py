from pymongo import MongoClient
import queue_writer
import time

from Queue import Queue
from threading import Thread
from processing import Classifier



# Define the access tokens and group_ids
access_token = "CAAK5npFF7MYBACPwdYQRuqHwmQj18YsRDdkUiU1WfyHvs2a5AaNzyNihyqXg1\
8UdGTyaJi9pWReXGQmJZAMtDpvOM8jqQ6c1GuvQLdKqLjvTHhyBIsYU26iLcLgUZAj4e9hnV9iyZAj\
wi4tr2gk5TAcNNJ71Nyctmzro1GFaikZCfVaoB42BS6AtEY6ypFZAxf6wpGUSYAjD3TMusTUeA"
group_id = '369653806521044'

print "\nStarting Mark Sweep (v0.1)"
print "Written by Jason Liu, Henry Boldizsar and Taylor Blau at PennApps X"
print "\n-----------------"

# Some constants, creates the queue and the workers
queue = Queue(maxsize=0)
num_workers = 8
write_interval = 3.5
clf = Classifier()

spam_threshold = .90

# mongo connection
client = MongoClient("mongodb://marksweep:pennapps@ds035300.mongolab.com:35300/marksweep")
db = client['marksweep']
logs = db['logs']


# Defines the action that will be taken on a given piece of data
def take_action(queue):
    while True:
        fb_entity = queue.get()
        msg = fb_entity.contents
        t = clf.process(msg)

        t['name'] = fb_entity.poster
        t['content'] = fb_entity.contents
        t['pid'] = fb_entity.post_id
        t['gid'] = fb_entity.group_id

        already_commented = False
        for comment in fb_entity.comments:
            if comment.poster['name'] == "Mark Sweep":
                already_commented = True
                break

        if not already_commented:
            percent_spam = "%.2f" % (t['spam'][1] * 100)
            t['spam_confidence'] =  percent_spam
            if t['spam'][1] > spam_threshold:
                fb_entity.post_comment("Hey! I\'m {}% sure this is probably spam, and has been marked for deletion. Please try and remain on topic for the discussion in this group!".format(percent_spam), access_token)
                t['status'] = "spam"
            else:
                if int(t['ontopic']) == 1:
                    fb_entity.post_comment('Hey, {}!  This post is on-topic\
                        with the discussion of the group.  Grats on a great\
                        post! (y)'.format(fb_entity.poster['name'].split(" ")[0]),
                        access_token)
                    t['status'] = "on_topic"
                elif t['spam'][1] > .80:
                    fb_entity.post_comment(':( We\'re not sure if this post\
                        belongs.  It looks like spam, but not entirely.  We\'re\
                        not sure!', access_token)
                    t['status'] = "maybe_spam"
                else:
                    fb_entity.post_comment('Uh-oh! This post doesn\'t appear\
                        to be on-topic with the rest of the group. Please keep\
                        discussion focused on the topic of the group.',
                        access_token)
                    t['status'] = "maybe_off_topic"
            del t['spam']
            logs.insert(t)

        queue.task_done()

# Spawn up the workers
for i in range(num_workers):
    print "Spawning up worker #{}".format(i + 1)
    worker = Thread(target=take_action, args=(queue,))
    worker.setDaemon(True)
    worker.start()

print "-----------------\n"

# Creates the queue writer
writer = queue_writer.QueueWriter(access_token, group_id)

# And finally, subscribe to the queue so that the program keeps running until
# everything is removed from the queue
print "Subscribing to the queue, ready to accept posts/comments...\n"
while True:
    try:
        writer.write(queue)
        # queue.join()

        time.sleep(write_interval)
    except KeyboardInterrupt:
        print "Shutting down..."
        break
