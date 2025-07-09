import typer
import yaml
import pyperclip
import json
import os
import glob
import re
from InquirerPy import inquirer
from typing import Dict, Any, List
from .models import PromptData, Template
from . import template_manager
from . import project_detector
from openai import OpenAI
from rich.console import Console
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.panel import Panel

app = typer.Typer()


@app.command("init")
def init():
    """Initialize a new PromptCraft project configuration."""
    typer.echo("🚀 Welcome to PromptCraft! Let's set up your project configuration.")

    # Ask user for project configuration
    framework = inquirer.text(
        message="What framework are you using?", default="FastAPI"
    ).execute()

    database = inquirer.text(
        message="What database are you using?", default="PostgreSQL"
    ).execute()

    style_guide = inquirer.text(
        message="What style guide do you follow?", default="PEP 8"
    ).execute()

    # Ask for LLM configuration
    llm_provider = inquirer.select(
        message="Choose LLM provider:",
        choices=["OpenAI", "Anthropic", "Other"],
        default="OpenAI"
    ).execute()

    llm_model = inquirer.text(
        message="Enter LLM model name:",
        default="gpt-4o-mini" if llm_provider == "OpenAI" else "claude-3-haiku-20240307"
    ).execute()

    # Create configuration dictionary
    config = {
        "framework": framework,
        "database": database,
        "style_guide": style_guide,
        "llm": {
            "provider": llm_provider,
            "model": llm_model
        }
    }

    # Write configuration to YAML file
    with open(".promptcraft.yml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    typer.echo("✅ Configuration saved to .promptcraft.yml")


@app.command("list")
def list_sessions():
    """List all saved prompt sessions."""
    promptcraft_dir = ".promptcraft"
    
    if not os.path.exists(promptcraft_dir):
        typer.echo("📁 No saved sessions found. Use 'promptcraft' to create and save sessions.")
        return
    
    # Find all .json files in the directory
    json_files = []
    for filename in os.listdir(promptcraft_dir):
        if filename.endswith('.json'):
            session_name = filename[:-5]  # Remove .json extension
            json_files.append(session_name)
    
    if not json_files:
        typer.echo("📁 No saved sessions found. Use 'promptcraft' to create and save sessions.")
        return
    
    typer.echo("📋 Saved Sessions:")
    for session_name in sorted(json_files):
        typer.echo(f"  • {session_name}")


@app.command("load")
def load_session(session_name: str):
    """Load a saved prompt session and start the interactive menu."""
    promptcraft_dir = ".promptcraft"
    filepath = os.path.join(promptcraft_dir, f"{session_name}.json")
    
    if not os.path.exists(filepath):
        typer.echo(f"❌ Session '{session_name}' not found.")
        typer.echo("💡 Use 'promptcraft list' to see available sessions.")
        return
    
    # Load the session data
    try:
        with open(filepath, "r") as f:
            session_data = json.load(f)
        
        # Create PromptData object from loaded data
        prompt_data = PromptData(
            persona=session_data.get("persona"),
            task=session_data.get("task"),
            context=session_data.get("context"),
            schemas=session_data.get("schemas", []),
            examples=session_data.get("examples", []),
            constraints=session_data.get("constraints")
        )
        
        typer.echo(f"✅ Loaded session '{session_name}'")
        
        # Start interactive menu with loaded data
        interactive_menu_with_data(prompt_data)
        
    except json.JSONDecodeError:
        typer.echo(f"❌ Error: Invalid JSON in session file '{session_name}'")
    except Exception as e:
        typer.echo(f"❌ Error loading session '{session_name}': {e}")


@app.command("run")
def run_session(session_name: str):
    """Run a prompt session against the configured LLM."""
    # Load project configuration
    config_path = ".promptcraft.yml"
    if not os.path.exists(config_path):
        typer.echo("❌ No configuration found. Run 'promptcraft init' first.")
        return
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        typer.echo(f"❌ Error loading configuration: {e}")
        return
    
    # Load session data
    promptcraft_dir = ".promptcraft"
    session_path = os.path.join(promptcraft_dir, f"{session_name}.json")
    
    if not os.path.exists(session_path):
        typer.echo(f"❌ Session '{session_name}' not found.")
        typer.echo("💡 Use 'promptcraft list' to see available sessions.")
        return
    
    try:
        with open(session_path, "r") as f:
            session_data = json.load(f)
    except Exception as e:
        typer.echo(f"❌ Error loading session: {e}")
        return
    
    # Create PromptData object
    prompt_data = PromptData(
        persona=session_data.get("persona"),
        task=session_data.get("task"),
        context=session_data.get("context"),
        schemas=session_data.get("schemas", []),
        examples=session_data.get("examples", []),
        constraints=session_data.get("constraints")
    )
    
    # Generate the prompt
    prompt_string = generate_prompt_string(prompt_data)
    
    if not prompt_string:
        typer.echo("❌ Session contains no data to generate a prompt.")
        return
    
    # Get LLM configuration
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "OpenAI")
    model = llm_config.get("model", "gpt-4o-mini")
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        typer.echo("❌ OPENAI_API_KEY environment variable not set.")
        typer.echo("💡 Set your API key: export OPENAI_API_KEY='your-key-here'")
        return
    
    # Create OpenAI client
    client = OpenAI(api_key=api_key)
    
    typer.echo(f"🚀 Running session '{session_name}' with {provider} {model}...")
    typer.echo("⏳ Generating response...")
    
    try:
        # Send request to OpenAI
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt_string}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extract the response content
        response_content = response.choices[0].message.content
        
        # Create Rich console for better output
        console = Console()
        
        # Display response with Rich formatting
        console.print("\n")
        console.print(Panel.fit("🤖 LLM Response", style="bold green"))
        
        # Use rich.markdown.Markdown to render the response
        markdown = Markdown(response_content)
        console.print(markdown)
        
    except Exception as e:
        typer.echo(f"❌ Error calling OpenAI API: {e}")


def handle_persona(prompt_data: PromptData):
    """Handle persona definition."""
    typer.echo("\n👤 Define Persona")
    typer.echo("Describe the role or character that will be responding to the task.")
    
    current_value = prompt_data.persona or ""
    persona = inquirer.text(
        message="Enter persona description:",
        default=current_value
    ).execute()
    
    prompt_data.persona = persona
    typer.echo(f"✅ Persona updated: {persona[:50]}{'...' if len(persona) > 50 else ''}")


def handle_task(prompt_data: PromptData):
    """Handle task specification."""
    typer.echo("\n📋 Specify the Task")
    typer.echo("Describe what you want the AI to accomplish.")

    current_value = prompt_data.task or ""
    task = inquirer.text(
        message="Enter task description:",
        default=current_value
    ).execute()

    prompt_data.task = task
    
    typer.echo(f"✅ Task updated: {task[:50]}{'...' if len(task) > 50 else ''}")


def get_path_suggestions(partial_path: str = "") -> List[str]:
    """Get file/directory suggestions for autocomplete based on partial path."""
    try:
        if not partial_path:
            # Show current directory contents
            current_dir = "."
            suggestions = []
        else:
            # Expand user path (~) 
            expanded_path = os.path.expanduser(partial_path)
            
            # If path ends with separator, list contents of that directory
            if expanded_path.endswith('/') or expanded_path.endswith('\\'):
                current_dir = expanded_path
                suggestions = []
            else:
                # Get directory part and filename part
                current_dir = os.path.dirname(expanded_path) or "."
                filename_part = os.path.basename(expanded_path)
                suggestions = []
        
        # Get all files and directories in current directory
        try:
            if os.path.exists(current_dir):
                items = os.listdir(current_dir)
                for item in items:
                    if item.startswith('.'):
                        continue
                    
                    item_path = os.path.join(current_dir, item)
                    if os.path.isdir(item_path):
                        suggestions.append(f"{item}/")
                    else:
                        suggestions.append(item)
        except Exception:
            pass
        
        # Filter suggestions based on partial input
        if partial_path and not (partial_path.endswith('/') or partial_path.endswith('\\')):
            filename_part = os.path.basename(partial_path)
            if filename_part:
                filtered = [s for s in suggestions if s.lower().startswith(filename_part.lower())]
                suggestions = filtered
        
        return sorted(suggestions)[:20]
    except Exception:
        return []

def parse_file_references(text: str) -> List[str]:
    """Parse @ file references from text."""
    # Find all @file_path patterns
    pattern = r'@([^\s]+)'
    matches = re.findall(pattern, text)
    return matches

def get_file_type(file_path: str) -> str:
    """Determine file type based on extension."""
    extension = os.path.splitext(file_path)[1].lower()
    
    if extension in ['.py']:
        return 'python'
    elif extension in ['.js', '.jsx', '.ts', '.tsx']:
        return 'javascript'
    elif extension in ['.java']:
        return 'java'
    elif extension in ['.go']:
        return 'go'
    elif extension in ['.rs']:
        return 'rust'
    elif extension in ['.c', '.cpp', '.cc', '.cxx', '.h', '.hpp']:
        return 'cpp'
    elif extension in ['.rb']:
        return 'ruby'
    elif extension in ['.php']:
        return 'php'
    else:
        return 'unknown'


def extract_python_context(file_path: str) -> str:
    """Extract Python-specific context like imports, classes, and functions."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        context_info = []
        
        # Extract imports
        imports = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line)
        
        if imports:
            context_info.append("**Imports:**")
            for imp in imports[:10]:  # Limit to first 10 imports
                context_info.append(f"- {imp}")
        
        # Extract class and function definitions
        definitions = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('class ') or line.startswith('def '):
                definitions.append(line)
        
        if definitions:
            context_info.append("\n**Definitions:**")
            for defn in definitions[:15]:  # Limit to first 15 definitions
                context_info.append(f"- {defn}")
        
        # Check for common Python patterns
        patterns = []
        if 'if __name__ == "__main__"' in content:
            patterns.append("- Has main execution block")
        if 'class ' in content and 'def __init__' in content:
            patterns.append("- Contains class definitions with constructors")
        if 'async def' in content or 'await ' in content:
            patterns.append("- Uses async/await patterns")
        if 'pytest' in content or 'unittest' in content:
            patterns.append("- Contains test code")
        
        if patterns:
            context_info.append("\n**Code Patterns:**")
            context_info.extend(patterns)
        
        return "\n".join(context_info)
    
    except Exception as e:
        return f"Error extracting Python context: {str(e)}"


def extract_javascript_context(file_path: str) -> str:
    """Extract JavaScript/TypeScript-specific context."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        context_info = []
        
        # Extract imports/requires
        imports = []
        for line in content.split('\n'):
            line = line.strip()
            if (line.startswith('import ') or line.startswith('const ') and 'require(' in line or 
                line.startswith('import {') or line.startswith('export ')):
                imports.append(line)
        
        if imports:
            context_info.append("**Imports/Exports:**")
            for imp in imports[:10]:  # Limit to first 10 imports
                context_info.append(f"- {imp}")
        
        # Extract function definitions
        functions = []
        for line in content.split('\n'):
            line = line.strip()
            if (line.startswith('function ') or line.startswith('const ') and '=>' in line or
                line.startswith('export function') or 'function(' in line):
                functions.append(line)
        
        if functions:
            context_info.append("\n**Functions:**")
            for func in functions[:10]:  # Limit to first 10 functions
                context_info.append(f"- {func}")
        
        # Check for common patterns
        patterns = []
        if 'React' in content or 'jsx' in file_path.lower():
            patterns.append("- React component")
        if 'useState' in content or 'useEffect' in content:
            patterns.append("- Uses React hooks")
        if 'async' in content and 'await' in content:
            patterns.append("- Uses async/await")
        if 'express' in content or 'app.get' in content:
            patterns.append("- Express.js server code")
        if 'describe(' in content or 'it(' in content or 'test(' in content:
            patterns.append("- Contains test code")
        
        if patterns:
            context_info.append("\n**Code Patterns:**")
            context_info.extend(patterns)
        
        # Check for package.json in same directory or parent
        package_json_path = None
        current_dir = os.path.dirname(file_path)
        for _ in range(3):  # Check up to 3 parent directories
            potential_package = os.path.join(current_dir, 'package.json')
            if os.path.exists(potential_package):
                package_json_path = potential_package
                break
            current_dir = os.path.dirname(current_dir)
        
        if package_json_path:
            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                    deps = list(package_data.get('dependencies', {}).keys())
                    if deps:
                        context_info.append(f"\n**Dependencies (from {package_json_path}):**")
                        for dep in deps[:8]:  # Limit to first 8 dependencies
                            context_info.append(f"- {dep}")
            except:
                pass
        
        return "\n".join(context_info)
    
    except Exception as e:
        return f"Error extracting JavaScript context: {str(e)}"


def read_file_content(file_path: str) -> str:
    """Read and return file content with error handling and smart context."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get file type and extract relevant context
        file_type = get_file_type(file_path)
        context_info = ""
        
        if file_type == 'python':
            context_info = extract_python_context(file_path)
        elif file_type == 'javascript':
            context_info = extract_javascript_context(file_path)
        
        # Build the formatted output
        result = f"\n## File: {file_path}\n"
        
        if context_info:
            result += f"\n**Context Information:**\n{context_info}\n"
        
        result += f"\n**File Content:**\n```\n{content}\n```\n"
        
        return result
    except Exception as e:
        return f"\n## File: {file_path}\n\n*Error reading file: {str(e)}*\n"

def process_context_with_files(context_text: str) -> str:
    """Process context text and expand file references."""
    file_refs = parse_file_references(context_text)
    
    if not file_refs:
        return context_text
    
    # Start with the original context
    processed_context = context_text
    
    # Add file contents
    for file_path in file_refs:
        file_content = read_file_content(file_path)
        processed_context += file_content
    
    return processed_context

def handle_context(prompt_data: PromptData):
    """Handle context provision with file reference support."""
    typer.echo("\n🔍 Provide Context")
    typer.echo("Provide background information, technical details, or relevant context.")
    typer.echo("💡 Tip: Use @filename to include file contents (e.g., @src/main.py)")
    
    current_value = prompt_data.context or ""
    
    # Ask if user wants to add a file
    add_file = inquirer.confirm(
        message="Would you like to add a file to context?",
        default=False
    ).execute()
    
    if add_file:
        def get_directory_contents(path):
            """Get files and directories in a given path."""
            try:
                expanded_path = os.path.expanduser(path)
                if not os.path.exists(expanded_path) or not os.path.isdir(expanded_path):
                    return []
                
                contents = []
                items = os.listdir(expanded_path)
                
                for item in items:
                    if item.startswith('.'):
                        continue
                    
                    item_path = os.path.join(expanded_path, item)
                    if os.path.isdir(item_path):
                        contents.append(f"{os.path.join(path, item)}/")
                    else:
                        contents.append(os.path.join(path, item))
                
                return sorted(contents)
            except Exception:
                return []
        
        # Start with current directory and common paths
        current_path = "."
        while True:
            # Get contents of current path
            all_files = get_directory_contents(current_path)
            
            # Add navigation options
            nav_options = []
            if current_path != ".":
                nav_options.append("⬆️  Go back")
            nav_options.extend([
                "📁 Current directory (.)",
                "🏠 Home directory (~)",
                "📂 Enter custom path"
            ])
            
            # Combine navigation and files
            choices = nav_options + all_files
            
            if not choices:
                typer.echo("No files found in directory.")
                break
            
            selected = inquirer.fuzzy(
                message=f"Select file from {current_path} (type to search):",
                choices=choices,
                validate=lambda x: True
            ).execute()
            
            if not selected:
                break
            elif selected == "⬆️  Go back":
                current_path = os.path.dirname(current_path) if current_path != "." else "."
            elif selected == "📁 Current directory (.)":
                current_path = "."
            elif selected == "🏠 Home directory (~)":
                current_path = "~"
            elif selected == "📂 Enter custom path":
                custom_path = inquirer.text(
                    message="Enter directory path:",
                    default=current_path
                ).execute()
                if custom_path:
                    current_path = custom_path
            elif selected.endswith('/'):
                # It's a directory, navigate into it
                current_path = selected
            else:
                # It's a file, select it
                current_value = f"{current_value}\n\n@{selected}" if current_value else f"@{selected}"
                break
    
    context = inquirer.text(
        message="Enter context information:",
        default=current_value,
        multiline=True
    ).execute()
    
    # Process the context to expand file references
    processed_context = process_context_with_files(context)
    prompt_data.context = processed_context
    
    # Show preview of what was added
    file_refs = parse_file_references(context)
    if file_refs:
        typer.echo(f"📁 Added files: {', '.join(file_refs)}")
    
    typer.echo(f"✅ Context updated: {context[:50]}{'...' if len(context) > 50 else ''}")


def handle_schemas(prompt_data: PromptData):
    """Handle schema definitions."""
    typer.echo("\n📐 Define Schemas")
    typer.echo("Add database schemas, data structures, or API definitions.")
    
    schema = inquirer.text(
        message="Enter schema definition (or press Enter to skip):",
        default=""
    ).execute()
    
    if schema.strip():
        prompt_data.schemas.append(schema)
        typer.echo(f"✅ Schema added: {schema[:50]}{'...' if len(schema) > 50 else ''}")
    
    typer.echo(f"📊 Total schemas: {len(prompt_data.schemas)}")


def handle_examples(prompt_data: PromptData):
    """Handle example additions."""
    typer.echo("\n💡 Add Examples")
    typer.echo("Provide examples of inputs, outputs, or code snippets.")
    
    example = inquirer.text(
        message="Enter example (or press Enter to skip):",
        default=""
    ).execute()
    
    if example.strip():
        prompt_data.examples.append(example)
        typer.echo(f"✅ Example added: {example[:50]}{'...' if len(example) > 50 else ''}")
    
    typer.echo(f"📝 Total examples: {len(prompt_data.examples)}")


def handle_constraints(prompt_data: PromptData):
    """Handle constraint setting."""
    typer.echo("\n⚠️  Set Constraints")
    typer.echo("Define limitations, requirements, or specific guidelines.")
    
    current_value = prompt_data.constraints or ""
    constraints = inquirer.text(
        message="Enter constraints:",
        default=current_value
    ).execute()
    
    prompt_data.constraints = constraints
    typer.echo(f"✅ Constraints updated: {constraints[:50]}{'...' if len(constraints) > 50 else ''}")


def generate_prompt_string(data: PromptData) -> str:
    """Generate a formatted Markdown prompt string from PromptData."""
    sections = []
    
    # Add persona section
    if data.persona:
        sections.append(f"# Persona\n\n{data.persona}")
    
    # Add task section
    if data.task:
        sections.append(f"# Task\n\n{data.task}")
    
    # Add context section
    if data.context:
        sections.append(f"# Context\n\n{data.context}")
    
    # Add schemas section
    if data.schemas:
        schemas_content = "\n\n".join(f"## Schema {i+1}\n\n{schema}" for i, schema in enumerate(data.schemas))
        sections.append(f"# Schemas\n\n{schemas_content}")
    
    # Add examples section
    if data.examples:
        examples_content = "\n\n".join(f"## Example {i+1}\n\n{example}" for i, example in enumerate(data.examples))
        sections.append(f"# Examples\n\n{examples_content}")
    
    # Add constraints section
    if data.constraints:
        sections.append(f"# Constraints\n\n{data.constraints}")
    
    # Join all sections with double newlines
    return "\n\n".join(sections)


def handle_save_session(prompt_data: PromptData):
    """Handle saving the current session to a file."""
    typer.echo("\n💾 Save Session")
    
    # Check if there's data to save
    if not any([prompt_data.persona, prompt_data.task, prompt_data.context, 
                prompt_data.schemas, prompt_data.examples, prompt_data.constraints]):
        typer.echo("❌ No data to save. Please fill out at least one section.")
        return
    
    # Get filename from user
    filename = inquirer.text(
        message="Enter session name (without extension):",
        default=""
    ).execute()
    
    if not filename.strip():
        typer.echo("❌ Session name cannot be empty.")
        return
    
    # Clean the filename
    filename = filename.strip().replace(" ", "_")
    
    # Create .promptcraft directory if it doesn't exist
    promptcraft_dir = ".promptcraft"
    if not os.path.exists(promptcraft_dir):
        os.makedirs(promptcraft_dir)
    
    # Prepare data for JSON serialization
    session_data = {
        "persona": prompt_data.persona,
        "task": prompt_data.task,
        "context": prompt_data.context,
        "schemas": prompt_data.schemas,
        "examples": prompt_data.examples,
        "constraints": prompt_data.constraints
    }
    
    # Save to JSON file
    filepath = os.path.join(promptcraft_dir, f"{filename}.json")
    try:
        with open(filepath, "w") as f:
            json.dump(session_data, f, indent=2)
        typer.echo(f"✅ Session saved as '{filename}' in {filepath}")
    except Exception as e:
        typer.echo(f"❌ Error saving session: {e}")


def handle_generate_and_copy(prompt_data: PromptData):
    """Handle prompt generation and clipboard copying."""
    typer.echo("\n✨ Generating Prompt...")
    
    # Generate the prompt string
    prompt_string = generate_prompt_string(prompt_data)
    
    if not prompt_string:
        typer.echo("❌ No data to generate prompt. Please fill out at least one section.")
        return
    
    # Copy to clipboard
    try:
        pyperclip.copy(prompt_string)
        typer.echo("✅ Prompt copied to clipboard!")
        
        # Show a preview of the generated prompt
        typer.echo("\n📋 Generated Prompt Preview:")
        typer.echo("-" * 50)
        
        # Show first 500 characters of the prompt
        preview = prompt_string[:500]
        if len(prompt_string) > 500:
            preview += "..."
        typer.echo(preview)
        typer.echo("-" * 50)
        
    except Exception as e:
        typer.echo(f"❌ Error copying to clipboard: {e}")
        typer.echo("📋 Generated Prompt:")
        typer.echo("-" * 50)
        typer.echo(prompt_string)
        typer.echo("-" * 50)






def get_menu_options(prompt_data: PromptData):
    """Generate menu options with completion indicators."""
    base_options = [
        ("👤 Define Persona", "persona"),
        ("📋 Specify the Task", "task"),
        ("🔍 Provide Context", "context"),
        ("📐 Define Schemas", "schemas"),
        ("💡 Add Examples", "examples"),
        ("⚠️  Set Constraints", "constraints"),
        ("💾 Save Session As...", None),
        ("✨ Generate and Copy Prompt ✨", None),
        ("🚪 Exit", None),
    ]
    
    menu_options = []
    for option, field in base_options:
        if field is None:
            menu_options.append(option)
        else:
            # Check if the field has content
            if field == "schemas":
                completed = bool(prompt_data.schemas)
            elif field == "examples":
                completed = bool(prompt_data.examples)
            else:
                completed = bool(getattr(prompt_data, field))
            
            if completed:
                menu_options.append(f"✅ {option[2:]}")
            else:
                menu_options.append(option)
    
    return menu_options, base_options

def get_next_step_index(current_choice, base_options):
    """Get the index of the next step after current choice."""
    # Find current step index
    current_index = -1
    for i, (option, field) in enumerate(base_options):
        if field is None:
            continue
        if current_choice.endswith(option[2:]) or current_choice == option:
            current_index = i
            break
    
    # Find next step that's not completed or is a core step
    for i in range(current_index + 1, len(base_options)):
        option, field = base_options[i]
        if field is not None and i < 6:  # Only advance through core steps (not Save/Generate/Exit)
            return i
    
    return current_index  # Stay on current if no next step

def interactive_menu_with_data(prompt_data: PromptData = None):
    """Run the main interactive menu for building prompts."""
    if prompt_data is None:
        prompt_data = PromptData()
    
    current_step_index = 0
    first_run = True

    while True:
        # Only show welcome message on first run
        if first_run:
            typer.echo("\n🚀 Welcome to PromptCraft!")
            
            # Detect project type and suggest templates
            try:
                project_description = project_detector.get_project_description()
                suggested_templates = project_detector.get_suggested_templates()
                
                if project_description != "Unknown project type":
                    typer.echo(f"🔍 Detected: {project_description}")
                    
                if suggested_templates:
                    templates_str = ", ".join(suggested_templates)
                    typer.echo(f"💡 Suggested templates: {templates_str}")
                    typer.echo("   Use 'promptcraft template use <name>' to load a template")
                    
            except Exception:
                # Silently fail if project detection has issues
                pass
            
            typer.echo("\nBuild your prompt by selecting from the options below:\n")
            first_run = False
        else:
            typer.echo("\n")

        menu_options, base_options = get_menu_options(prompt_data)
        current_default = menu_options[current_step_index]

        # Get user's choice
        choice = inquirer.select(
            message="Select an option:",
            choices=menu_options,
            default=current_default,
        ).execute()

        # If user cancels (e.g., Ctrl+C), choice can be None
        if choice is None:
            typer.echo("👋 Goodbye!")
            break
        
        # Use a simple, direct if/elif/else chain to handle the choice
        if choice == "🚪 Exit":
            typer.echo("👋 Goodbye!")
            break
        elif choice.endswith("Define Persona") or choice == "👤 Define Persona":
            handle_persona(prompt_data)
            current_step_index = get_next_step_index(choice, base_options)
        elif choice.endswith("Specify the Task") or choice == "📋 Specify the Task":
            handle_task(prompt_data)
            current_step_index = get_next_step_index(choice, base_options)
        elif choice.endswith("Provide Context") or choice == "🔍 Provide Context":
            handle_context(prompt_data)
            current_step_index = get_next_step_index(choice, base_options)
        elif choice.endswith("Define Schemas") or choice == "📐 Define Schemas":
            handle_schemas(prompt_data)
            current_step_index = get_next_step_index(choice, base_options)
        elif choice.endswith("Add Examples") or choice == "💡 Add Examples":
            handle_examples(prompt_data)
            current_step_index = get_next_step_index(choice, base_options)
        elif choice.endswith("Set Constraints") or choice == "⚠️  Set Constraints":
            handle_constraints(prompt_data)
            current_step_index = get_next_step_index(choice, base_options)
        elif choice.endswith("Save Session As...") or choice == "💾 Save Session As...":
            handle_save_session(prompt_data)
            # Stay on current step for save
        elif choice.endswith("Generate and Copy Prompt ✨") or choice == "✨ Generate and Copy Prompt ✨":
            handle_generate_and_copy(prompt_data)
            typer.echo("👋 Goodbye!")
            break
        else:
            # This case should ideally not be reached with fuzzy matching
            typer.echo(f"Unknown option: {choice}")



def interactive_menu():
    """Run the main interactive menu for building prompts."""
    interactive_menu_with_data()


# Template management commands
template_app = typer.Typer(help="Template management commands")
app.add_typer(template_app, name="template")


@template_app.command("list")
def list_templates():
    """List all available templates."""
    templates = template_manager.load_templates()
    
    if not templates:
        typer.echo("📁 No templates found.")
        return
    
    typer.echo("📋 Available Templates:")
    for template in templates:
        tags_str = ", ".join(template.tags) if template.tags else "no tags"
        typer.echo(f"  • {template.name}: {template.description}")
        typer.echo(f"    Tags: {tags_str}")
        typer.echo()


@template_app.command("show")
def show_template(name: str):
    """Show detailed information about a template."""
    template = template_manager.load_template(name)
    
    if not template:
        typer.echo(f"❌ Template '{name}' not found.")
        typer.echo("💡 Use 'promptcraft template list' to see available templates.")
        return
    
    console = Console()
    
    # Display template details with Rich formatting
    console.print(f"\n📋 Template: {template.name}", style="bold blue")
    console.print(f"Description: {template.description}")
    console.print(f"Tags: {', '.join(template.tags) if template.tags else 'None'}")
    
    if template.persona:
        console.print(f"\n👤 Persona:")
        console.print(Panel(template.persona, style="cyan"))
    
    if template.task:
        console.print(f"\n📋 Task:")
        console.print(Panel(template.task, style="green"))
    
    if template.context:
        console.print(f"\n🔍 Context:")
        console.print(Panel(template.context, style="yellow"))
    
    if template.constraints:
        console.print(f"\n⚠️  Constraints:")
        console.print(Panel(template.constraints, style="red"))


@template_app.command("use")
def use_template(name: str):
    """Load a template and start the interactive menu."""
    template = template_manager.load_template(name)
    
    if not template:
        typer.echo(f"❌ Template '{name}' not found.")
        typer.echo("💡 Use 'promptcraft template list' to see available templates.")
        return
    
    # Convert template to PromptData
    prompt_data = template.to_prompt_data()
    
    typer.echo(f"✅ Loaded template '{name}'")
    typer.echo(f"📝 {template.description}")
    
    # Start interactive menu with loaded template data
    interactive_menu_with_data(prompt_data)


@app.command("quick")
def quick(
    template: str = typer.Option("code-review", help="Template to use"),
    file: str = typer.Option(None, help="File to include in context"),
    output: bool = typer.Option(False, help="Output to stdout instead of clipboard")
):
    """Quick prompt generation."""
    # Load the specified template
    template_obj = template_manager.load_template(template)
    
    if not template_obj:
        typer.echo(f"❌ Template '{template}' not found.")
        typer.echo("💡 Use 'promptcraft template list' to see available templates.")
        return
    
    # Convert template to PromptData
    prompt_data = template_obj.to_prompt_data()
    
    # Include file content if specified
    if file:
        if not os.path.exists(file):
            typer.echo(f"❌ File '{file}' not found.")
            return
        
        try:
            # Read file content and add to context
            file_content = read_file_content(file)
            if prompt_data.context:
                prompt_data.context += f"\n\n{file_content}"
            else:
                prompt_data.context = file_content
        except Exception as e:
            typer.echo(f"❌ Error reading file '{file}': {e}")
            return
    
    # Generate the prompt string
    prompt_string = generate_prompt_string(prompt_data)
    
    if not prompt_string:
        typer.echo("❌ Failed to generate prompt.")
        return
    
    # Output to stdout or clipboard based on option
    if output:
        typer.echo("📋 Generated Prompt:")
        typer.echo("-" * 50)
        typer.echo(prompt_string)
        typer.echo("-" * 50)
    else:
        try:
            pyperclip.copy(prompt_string)
            typer.echo("✅ Prompt copied to clipboard!")
            typer.echo(f"📋 Used template: {template}")
            if file:
                typer.echo(f"📁 Included file: {file}")
        except Exception as e:
            typer.echo(f"❌ Error copying to clipboard: {e}")
            typer.echo("📋 Generated Prompt:")
            typer.echo("-" * 50)
            typer.echo(prompt_string)
            typer.echo("-" * 50)


@app.command("review")
def review_file(file_path: str):
    """Quick code review of a file."""
    quick(template="code-review", file=file_path, output=False)


@app.command("debug")
def debug_issue(error_message: str):
    """Generate debugging prompt for an error message."""
    # Create a temporary file with the error message
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write(f"Error Message:\n{error_message}")
        temp_file_path = temp_file.name
    
    try:
        # Load debugging template
        template_obj = template_manager.load_template("debugging")
        if not template_obj:
            typer.echo("❌ Debugging template not found.")
            return
        
        # Convert template to PromptData and add error message to context
        prompt_data = template_obj.to_prompt_data()
        error_context = f"Error Message: {error_message}\n\nPlease analyze this error and provide debugging steps."
        
        if prompt_data.context:
            prompt_data.context += f"\n\n{error_context}"
        else:
            prompt_data.context = error_context
        
        # Generate and copy prompt
        prompt_string = generate_prompt_string(prompt_data)
        
        try:
            pyperclip.copy(prompt_string)
            typer.echo("✅ Debugging prompt copied to clipboard!")
            typer.echo(f"🐛 Error: {error_message[:50]}{'...' if len(error_message) > 50 else ''}")
        except Exception as e:
            typer.echo(f"❌ Error copying to clipboard: {e}")
            typer.echo("📋 Generated Prompt:")
            typer.echo("-" * 50)
            typer.echo(prompt_string)
            typer.echo("-" * 50)
    
    finally:
        # Clean up temporary file
        import os
        try:
            os.unlink(temp_file_path)
        except:
            pass


@app.command("explain")
def explain_file(file_path: str):
    """Generate explanation prompt for a file."""
    # Create a custom template for code explanation
    template_obj = template_manager.load_template("code-review")
    if not template_obj:
        typer.echo("❌ Code review template not found.")
        return
    
    # Convert template to PromptData and modify for explanation
    prompt_data = template_obj.to_prompt_data()
    prompt_data.persona = "You are an expert code educator who excels at explaining complex code in simple, understandable terms."
    prompt_data.task = "Explain the provided code in detail. Break down its functionality, purpose, and how it works step by step."
    prompt_data.constraints = "Provide clear explanations suitable for someone learning the codebase. Include purpose, key functions, data flow, and any important patterns or concepts."
    
    # Include file content if it exists
    if not os.path.exists(file_path):
        typer.echo(f"❌ File '{file_path}' not found.")
        return
    
    try:
        file_content = read_file_content(file_path)
        if prompt_data.context:
            prompt_data.context += f"\n\n{file_content}"
        else:
            prompt_data.context = file_content
    except Exception as e:
        typer.echo(f"❌ Error reading file '{file_path}': {e}")
        return
    
    # Generate and copy prompt
    prompt_string = generate_prompt_string(prompt_data)
    
    try:
        pyperclip.copy(prompt_string)
        typer.echo("✅ Code explanation prompt copied to clipboard!")
        typer.echo(f"📄 File: {file_path}")
    except Exception as e:
        typer.echo(f"❌ Error copying to clipboard: {e}")
        typer.echo("📋 Generated Prompt:")
        typer.echo("-" * 50)
        typer.echo(prompt_string)
        typer.echo("-" * 50)


@app.command("test")
def test_file(file_path: str):
    """Generate test case prompt for a file."""
    quick(template="testing", file=file_path, output=False)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """PromptCraft - A CLI for crafting high-quality LLM prompts."""
    if ctx.invoked_subcommand is None:
        interactive_menu()


if __name__ == "__main__":
    app()
