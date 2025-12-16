require 'yaml'
require 'digest'
require 'jekyll'

module Jekyll
  class GenerateChaptersData < Generator
    safe true

    def generate(site)
      chapters = []
      chapters_dir = File.join(site.source, '_pages', 'chapters')

      unless File.directory?(chapters_dir)
        Jekyll.logger.info "Skipping _pages/chapters (directory not found); generating empty _data/chapters.yml"
        chapters_data_yaml = YAML.dump(chapters)
        chapters_data_hash = Digest::SHA256.hexdigest(chapters_data_yaml)

        current_hash = ''
        data_file_path = File.join(site.source, '_data', 'chapters.yml')
        if File.exist?(data_file_path)
          current_hash = Digest::SHA256.hexdigest(File.read(data_file_path))
        end

        if current_hash != chapters_data_hash
          Dir.mkdir(File.dirname(data_file_path)) unless Dir.exist?(File.dirname(data_file_path))
          File.open(data_file_path, 'w') { |file| file.write(chapters_data_yaml) }
          Jekyll.logger.info "Regenerated _data/chapters.yml"
        else
          Jekyll.logger.info "No changes to _data/chapters.yml"
        end

        return
      end

      Dir.foreach(chapters_dir) do |chapter|
        next if chapter == '.' || chapter == '..'

        chapter_path = File.join(chapters_dir, chapter)
        next unless File.directory?(chapter_path)

        chapter_data = {
          'name' => format_name(chapter),
          'files' => []
        }

        Dir.foreach(chapter_path) do |file|
          next if file == '.' || file == '..' || File.directory?(File.join(chapter_path, file))

          file_path = File.join(chapter_path, file)
          front_matter = read_front_matter(file_path)
          file_data = {
            'name' => front_matter['title'] || format_name(file),
            'path' => generate_jekyll_path(chapter, file)
          }

          chapter_data['files'] << file_data
        end

        chapters << chapter_data
      end

      # Generate the YAML data
      chapters_data_yaml = YAML.dump(chapters)
      chapters_data_hash = Digest::SHA256.hexdigest(chapters_data_yaml)

      # Check if the current file exists and read its hash
      current_hash = ''
      data_file_path = File.join(site.source, '_data', 'chapters.yml')
      if File.exist?(data_file_path)
        current_hash = Digest::SHA256.hexdigest(File.read(data_file_path))
      end

      # Only regenerate _data/chapters.yml if its content has changed
      if current_hash != chapters_data_hash
        Dir.mkdir(File.dirname(data_file_path)) unless Dir.exist?(File.dirname(data_file_path))
        File.open(data_file_path, 'w') do |file|
          file.write(chapters_data_yaml)
        end
        Jekyll.logger.info "Regenerated _data/chapters.yml"
      else
        Jekyll.logger.info "No changes to _data/chapters.yml"
      end
    end

    def format_name(name)
      name.split('-').map(&:capitalize).join(' ')
    end

    def read_front_matter(file_path)
      content = File.read(file_path)
      front_matter = content.match(/---\s*\n(.*?)\n---\s*\n/m)
      front_matter ? YAML.safe_load(front_matter[1]) : {}
    end

    def generate_jekyll_path(chapter, file)
      file_basename = File.basename(file, File.extname(file))
      File.join('/chapters', chapter, file_basename, 'index.html')
    end
  end
end
