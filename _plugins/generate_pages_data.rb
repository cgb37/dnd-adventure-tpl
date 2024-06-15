require 'yaml'
require 'digest'
require 'jekyll'

module Jekyll
  class GenerateDataFiles < Generator
    safe true

    def generate(site)
      @site = site
      generate_data_for_dir('monsters', %w[title permalink chapter episode scene category thumb])
      generate_data_for_dir('npcs', %w[title permalink chapter episode scene category thumb])
      generate_data_for_dir('encounters', %w[title permalink chapter episode scene category thumb])
      generate_data_for_dir('locations', %w[title permalink chapter episode scene category thumb])
    end

    private

    def generate_data_for_dir(dir_name, required_keys)
      data = []
      dir_path = File.join(@site.source, '_pages', dir_name)

      Dir.foreach(dir_path) do |file|
        next if file == '.' || file == '..'

        file_path = File.join(dir_path, file)
        next unless File.file?(file_path)

        front_matter = read_front_matter(file_path)
        next if front_matter.empty? || missing_required_keys?(front_matter, required_keys)

        data_item = {}
        required_keys.each do |key|
          if key == 'permalink'
            data_item[key] = generate_permalink(front_matter[key], front_matter['title'])
          else
            data_item[key] = front_matter[key] || ''
          end
        end
        data << data_item
      end

      generate_data_file(dir_name, data)
    end

    def read_front_matter(file_path)
      content = File.read(file_path)
      front_matter = content.match(/---\s*\n(.*?)\n---\s*\n/m)
      front_matter ? YAML.safe_load(front_matter[1]) : {}
    end

    def missing_required_keys?(front_matter, required_keys)
      required_keys.any? { |key| !front_matter.key?(key) }
    end

    def generate_permalink(permalink_template, title)
      slug = title.downcase.gsub(/\s+/, '-').gsub(/[^a-z0-9\-]/, '').gsub(/\-+/, '-').gsub(/^-|-$/, '')
      permalink_template.gsub(/:slug/, slug)
    end

    def generate_data_file(dir_name, data)
      data_yaml = YAML.dump(data)
      data_hash = Digest::SHA256.hexdigest(data_yaml)

      current_hash = ''
      data_file_path = File.join(@site.source, '_data', "#{dir_name}.yml")
      if File.exist?(data_file_path)
        current_hash = Digest::SHA256.hexdigest(File.read(data_file_path))
      end

      if current_hash != data_hash
        Dir.mkdir(File.dirname(data_file_path)) unless Dir.exist?(File.dirname(data_file_path))
        File.open(data_file_path, 'w') do |file|
          file.write(data_yaml)
        end
        Jekyll.logger.info "Regenerated _data/#{dir_name}.yml"
      else
        Jekyll.logger.info "No changes to _data/#{dir_name}.yml"
      end
    end
  end
end