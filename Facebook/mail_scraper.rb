#!/usr/bin/env ruby

require 'rubygems'
require 'nokogiri'
require 'mechanize'
require 'time'

$debug = true

class FacebookMessage
  attr_accessor :from_username, :from_userid, :sent_at, :subject, :body
  def initialize(from_username, from_userid, sent_at, subject, body)
    @from_username = from_username
    @from_userid = from_userid
    @sent_at = sent_at
    @subject = subject
    @body = body
  end
  
  def to_s
    "
From: #{from_username} (#{from_userid})
Subject: #{subject}
Sent at: #{sent_at}

#{body}
"
  end
end

class FacebookMessageParser

  def initialize()
    @fbUrl = "http://www.facebook.com"
    @agent = WWW::Mechanize.new
    @agent.user_agent_alias  = "Mac Safari"

    # Env vars from LifeDB
    @username = ENV['LIFEDB_USERNAME']
    @password = ENV['LIFEDB_PASSWORD']
    @datadir = ENV['LIFEDB_DIR']
    @cachedir = ENV['LIFEDB_CACHE_DIR']
    
    [:username, :password, :datadir, :statedir].each do |p|
      if self.send(username).nil?
        $stderr.puts "Failed to find #{p} in ENV"
        exit(1)
      end
    end

    # Set this up manually, just in case we're using an old version
    WWW::Mechanize.html_parser = Nokogiri::HTML
  end
  
  def parse
    login_result = login()

    puts "Login #{login_result ? "succeeded" : "failed"}" if $debug

    if (login_result)

      mail_page = @agent.get("http://www.facebook.com/inbox/")

      while (true)
        threads_to_traverse = get_thread_links(mail_page)
        
        threads_to_traverse.each do |link, last_message_timestamp|
          
          get_and_store_message(link, last_message_timestamp)
          
          
          
        end
        
        next_page_link = get_next_page_link(mail_page)
        
        if next_page_link.nil?
          break
        else
          puts "Getting page #{next_page_link['href']}" if $debug
          mail_page = @agent.get(next_page_link['href'])
        end
      end # end while(true)
      
      pages_to_traverse = get_pagination_links(mail_page)


      messages_to_traverse.each do |message|
        random_sleep()
        puts "Parsing #{message['href']}" if $debug

        message_page = @agent.get(message['href'])
        parse_message_page(message_page)
      end
    end
  end
  
  private
  
  def login
    puts "Logging in..."
    page = @agent.get(@fbUrl)

    if(page.title == "Welcome to Facebook! | Facebook")
      loginf = page.form('menubar_login')
      loginf.email = @username
      loginf.pass = @password
      login_result_page = @agent.submit(loginf, loginf.buttons.first)
      
      # Return true if we've arrived at the home page
      (login_result_page.title == "Facebook | Home")
    end
  end

  # Returns a list of the pagination links at the footer of the FB mail page
  def get_pagination_links(mail_page)
    mail_page.search('ul.pagerpro li a').collect
  end
  
  def get_next_page_link(mail_page)
    pagination_links = get_pagination_links(mail_page)
    pagination_links.find { |x| x.content == "Next" }
  end

  # Returns a list of message links for this page
  def get_thread_links(mail_page)
    puts "Getting thread links..." if $debug
    mail_page.search('table#megaboxx tr').collect do |x|
      thread_link = x.search("div.subject_wrap a").first
      raw_time = x.search(".name_and_date .date").first.content
      
      puts "  Thread link: #{thread_link['href']}" if $debug
      puts "  Time: #{raw_time}" if $debug
      
      [thread_link, Time.parse(raw_time)]
    end 
  end

  def random_sleep
    duration = ((rand * 10) + 3).to_i
    puts "Sleeping for #{duration}s" if $debug
    sleep duration
  end

  def get_and_store_message(thread_link, last_message_timestamp)
    message_subject = message_page.search(".thread_header h2.subject").first.child.content
    
    messages = message_page.search("div.message").collect
    
    messages.reverse!
    
    messages.each do |message|
      sender_href = message.search(".author_info .name a").first['href']
      
      message_date = Time.parse(message.search(".author_info .date").first.content)
      message_body = message.search(".body .text").first.content
      message_from_facebook_name = message.search(".author_info .name").first.content
    
      if sender_href =~ /id=(\d+)$/
        message_from_facebook_id = $1
      else
        message_from_facebook_id = -1
      end
    
      msg = FacebookMessageParser.new(message_from_facebook_name,
                                      message_from_facebook_id,
                                      message_date,
                                      message_subject,
                                      message_body)
    end
  end
  
  def 
end

# MAIN

f = Facebook.new
f.parse
exit(0)