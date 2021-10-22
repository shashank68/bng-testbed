#!/bin/bash

kill -15 $(ip netns pids n0)
kill -15 $(ip netns pids n1)

ip netns del n0
ip netns del n1
