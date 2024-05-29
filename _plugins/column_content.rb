puts "Loading custom column tags plugin..."

module Jekyll
  class ColumnBlock < Liquid::Block
    def initialize(tag_name, markup, tokens)
      super
      @column = markup.strip
    end

    def render(context)
      content = super
      "<div class='col-6'>#{content}</div>"
    end
  end
end

Liquid::Template.register_tag('start_column1', Jekyll::ColumnBlock)
Liquid::Template.register_tag('start_column2', Jekyll::ColumnBlock)
