require 'json'

module Jekyll
  class SearchJsonGenerator < Generator
    safe true

    def generate(site)
      search_data = []

      site.collections['pages'].docs.each do |page|
        if page.data['search'] == true
          search_data << {
            title: page.data['title'],
            url: page.url,
            content: page.content.gsub(/<[^>]*>/, '').gsub("\n", ' ').strip,
            chapter: page.data['chapter']
          }
        end
      end

      # Debug output to verify the content of search_data
      Jekyll.logger.info "search_data:", search_data.inspect

      File.open('search.json', 'w') do |file|
        file.write(JSON.pretty_generate(search_data))
      end
    end
  end
end
