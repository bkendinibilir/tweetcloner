#!/usr/bin/env python
# 
### LICENSE
#
# Copyright (c) 2012, Benjamin Kendinibilir <bkendinibilir@me.com>
# 
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above 
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
# 

import os, sys, argparse
import ConfigParser
import tweepy

class TweetCloner:
	TWEETCLONER_CONSUMER_KEY='SscEYZXGFrof1Hzt8j9EOQ'
	TWEETCLONER_CONSUMER_SECRET='8dbW5YzqVEyaXlctGKNEMmNb4sB5DP0UKXzE3qVZDY'

	def __init__(self, configfile):
		self.src_account = ""
		self.dst_accounts = []
		self.initial_tweetcount = 1
		self.dry_run = False
		self.configfile = configfile

		self.read_config()

	def read_config(self):
		cfg = self.configfile

		if not os.path.isfile(cfg):
			answer = raw_input('Cannot find configfile "{0}", create empty one? (y/N): '. 
				format(cfg)).strip()
			if answer == 'y':
				try:
					open(cfg, 'w').close()
				except:
					sys.stderr.write('ERROR: Cannot create configfile.')
					sys.exit(1)
			
		if not os.access(cfg, os.R_OK | os.W_OK):
			sys.stderr.write('ERROR: Cannot open configfile "{0}". Missing or no read/write access.\n'. format(cfg))
			sys.exit(1)

		self.config = ConfigParser.ConfigParser()
		self.config.read(cfg)

	def save_config(self):
	  	with open(self.configfile, 'wb') as cfg:
			self.config.write(cfg)

	def check_config(self):	
		self.check_cfg_section(self.src_account)
		for dst_account in self.dst_accounts:
			self.check_cfg_section(dst_account)

	def check_cfg_section(self, section):
		if not self.config.has_section(section):
			sys.stderr.write('Cannot find section for account "{0}" in configfile "{1}".\n'.
				format(section, self.configfile))
			answer = raw_input('Do you want to add a new section for "{0}" as a new twitter account? (y/N): '.
				format(section)).strip()
			if answer == 'y':
				self.config.add_section(section)
				self.config.set(section, "consumer_key", self.TWEETCLONER_CONSUMER_KEY)
				self.config.set(section, "consumer_secret", self.TWEETCLONER_CONSUMER_SECRET)
				self.save_config()
			else:
				sys.stderr.write('ERROR: Account not found. Exit.\n')
				sys.exit(1)

		if not self.config.has_option(section, 'access_key') or \
		   not self.config.has_option(section, 'access_secret'):
			print 'Missing access_key and/or access_secret for {0}, requesting new token...'.format(section)
			self.oauth_app(section)
	
	def get_api(self, service):
		if not self.config.has_option(service, 'consumer_key') or \
		   not self.config.has_option(service, 'consumer_secret'):
			sys.stderr.write('ERROR: Missing consumer_key or consumer_secret for {0} in configfile "{1}".\n'.
				format(service, self.configfile))
			sys.exit(1)
	
		auth = tweepy.OAuthHandler(self.config.get(service, 'consumer_key'), 
			self.config.get(service, 'consumer_secret'), 'oob')
		
		s_host = auth.OAUTH_HOST
		s_oroot = auth.OAUTH_ROOT
		s_aroot = '/1'
	
		if self.config.has_option(service, 'host'):
			s_host = self.config.get(service, 'host') 
		if self.config.has_option(service, 'oauth_root'):
			s_oroot = self.config.get(service, 'oauth_root')
		if self.config.has_option(service, 'api_root'):
			s_aroot = self.config.get(service, 'api_root')
	
		auth.OAUTH_HOST = s_host
		auth.OAUTH_ROOT = s_oroot
		auth.secure = True 
	
		auth.set_access_token(self.config.get(service, 'access_key'), 	
			self.config.get(service, 'access_secret'))
	
		return tweepy.API(auth, host = s_host, api_root = s_aroot, secure = True)
	
	def save_access_token(self, auth, service):
		auth_url = auth.get_authorization_url()
	
		print 'Please authorize TweetCloner app at: \n ' + auth_url
		pin = raw_input('Please enter PIN: ').strip()
	
		auth.get_access_token(pin)
		print '* Saving access_key and access_secret for account "{0}" in configfile.'.format(service)
		self.config.set(service, 'access_key', auth.access_token.key)
		self.config.set(service, 'access_secret', auth.access_token.secret)
		self.save_config()
	
	def oauth_app(self, service):
		auth = tweepy.OAuthHandler(self.config.get(service, 'consumer_key'), 
			self.config.get(service, 'consumer_secret'), 'oob')
	
		if self.config.has_option(service, 'host'):
			auth.OAUTH_HOST = self.config.get(service, 'host')
		if self.config.has_option(service, 'oauth_root'):
			auth.OAUTH_ROOT = self.config.get(service, 'oauth_root')
		auth.secure = True 
	
		self.save_access_token(auth, service)
	
	def clone(self):	
		self.check_config()

		src = self.src_account
		s_api = self.get_api(src)
	
		if self.config.has_option(src, 'last_id'):
			last_id = self.config.getint(src, 'last_id')
			t_timeline = s_api.user_timeline(since_id = last_id)
		else:
			last_id = 0
			t_timeline = s_api.user_timeline(count = self.initial_tweetcount)
		
		if len(t_timeline) > 0:
			for dst in self.dst_accounts: 
				d_api = self.get_api(dst)
		
				t_timeline.reverse()
				for status in t_timeline:
					try:
						if not self.config.has_option(src, 'filter') or \
							any((True for x in self.config.get(src, 'filter').split(',') if x in status.text)):
							
							newstatus = status.text	
							if self.config.has_option(dst, 'replace'):
								for replaces in self.config.get(dst, 'replace').split(','):
									replace = replaces.split('=')
									newstatus = newstatus.replace(replace[0], replace[1])
							
							print '* Posting to account "{0}": "{1}"'.format(dst, newstatus)
							if not self.dry_run:
								d_api.update_status(newstatus)
						else:
							print '* Skipping post (filter not matched): "{0}"'.format(status.text)
					except ValueError:
						pass	
					if last_id < status.id:
						last_id = status.id
	
			if last_id > 0:
				print '* Saving last_id of account "{0}": {1}'.format(src, last_id)
				if not self.dry_run:
					self.config.set(src, 'last_id', last_id)
					self.save_config()

def main():
	parser = argparse.ArgumentParser(prog='tweetcloner.py',
		description='Clone status updates (tweets) from and to microblogging systems '
		'with twitter-compatible API like Twitter, Identi.ca, Status.net, Yammer, etc.')
	parser.add_argument('src_account', 
		help='source account, where tweets are copied from.')
	parser.add_argument('dst_account', nargs='+',
		help='destination accounts, where the tweets are cloned to.')
	parser.add_argument('-c', '--config', default='tweetcloner.cfg', 
		help='path to config file (default: tweetcloner.cfg)')
	parser.add_argument('--dry-run', action='store_true',
		help='show what would have been cloned, no writing')
	parser.add_argument('--version', action='version', version='%(prog)s v0.5')
	
	args = parser.parse_args()

	tc = TweetCloner(args.config)
	tc.src_account  = args.src_account
	tc.dst_accounts = args.dst_account
	tc.dry_run      = args.dry_run

	tc.clone()

if __name__ == '__main__':
	main()

