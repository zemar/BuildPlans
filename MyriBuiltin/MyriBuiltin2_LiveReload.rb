# frozen_string_literal: true

# Load this file once from SketchUp's Ruby Console. It watches MyriBuiltin2.rb
# and automatically reloads it whenever VS Code saves the file.

module MyriBuiltin2LiveReload
  class << self
    def start
      stop
      @script_path = File.expand_path('MyriBuiltin2.rb', __dir__)
      @last_modified = nil
      reload_script
      @timer_id = UI.start_timer(0.75, true) { reload_if_changed }
      puts("Myri Built-in 2 live reload watching: #{@script_path}")
    end

    def stop
      return unless @timer_id

      UI.stop_timer(@timer_id)
      @timer_id = nil
      puts('Myri Built-in 2 live reload stopped')
    end

    def reload_if_changed
      modified = File.mtime(@script_path)
      return if @last_modified && modified <= @last_modified

      reload_script
    rescue StandardError, ScriptError => error
      report_error(error)
    end

    def reload_script
      @last_modified = File.mtime(@script_path)
      load(@script_path)
      Sketchup.status_text = 'Myri Built-in 2 reloaded from VS Code'
    rescue StandardError, ScriptError => error
      report_error(error)
    end

    private

    def report_error(error)
      Sketchup.status_text = "Myri Built-in 2 error: #{error.message}"
      warn("Myri Built-in 2 live-reload error: #{error.message}")
      warn(error.backtrace.join("\n"))
    end
  end
end

MyriBuiltin2LiveReload.start
