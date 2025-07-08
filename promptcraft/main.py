import typer
import yaml
import pyperclip
import json
import os
from InquirerPy import inquirer
from typing import Dict, Any
from .models import PromptData
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


def handle_context(prompt_data: PromptData):
    """Handle context provision."""
    typer.echo("\n🔍 Provide Context")
    typer.echo("Provide background information, technical details, or relevant context.")
    
    current_value = prompt_data.context or ""
    context = inquirer.text(
        message="Enter context information:",
        default=current_value
    ).execute()
    
    prompt_data.context = context
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






def interactive_menu_with_data(prompt_data: PromptData = None):
    """Run the main interactive menu for building prompts."""
    if prompt_data is None:
        prompt_data = PromptData()

    while True:
        typer.echo("\n🚀 Welcome to PromptCraft!")
        typer.echo("Build your prompt by selecting from the options below:\n")

        # Define the clear, descriptive menu options
        menu_options = [
            "👤 Define Persona",
            "📋 Specify the Task",
            "🔍 Provide Context",
            "📐 Define Schemas",
            "💡 Add Examples",
            "⚠️  Set Constraints",
            "💾 Save Session As...",
            "✨ Generate and Copy Prompt ✨",
            "🚪 Exit",
        ]

        # Get user's choice
        choice = inquirer.fuzzy(
            message="Select an option:",
            choices=menu_options,
            default=menu_options[0],
        ).execute()

        # If user cancels (e.g., Ctrl+C), choice can be None
        if choice is None:
            typer.echo("👋 Goodbye!")
            break
        
        # Use a simple, direct if/elif/else chain to handle the choice
        if choice == "🚪 Exit":
            typer.echo("👋 Goodbye!")
            break
        elif choice == "👤 Define Persona":
            handle_persona(prompt_data)
        elif choice == "📋 Specify the Task":
            handle_task(prompt_data)
        elif choice == "🔍 Provide Context":
            handle_context(prompt_data)
        elif choice == "📐 Define Schemas":
            handle_schemas(prompt_data)
        elif choice == "💡 Add Examples":
            handle_examples(prompt_data)
        elif choice == "⚠️  Set Constraints":
            handle_constraints(prompt_data)
        elif choice == "💾 Save Session As...":
            handle_save_session(prompt_data)
        elif choice == "✨ Generate and Copy Prompt ✨":
            handle_generate_and_copy(prompt_data)
        else:
            # This case should ideally not be reached with fuzzy matching
            typer.echo(f"Unknown option: {choice}")



def interactive_menu():
    """Run the main interactive menu for building prompts."""
    interactive_menu_with_data()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """PromptCraft - A CLI for crafting high-quality LLM prompts."""
    if ctx.invoked_subcommand is None:
        interactive_menu()


if __name__ == "__main__":
    app()
