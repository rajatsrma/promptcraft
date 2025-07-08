# PromptCraft CLI

A command-line interface for crafting high-quality, structured, and context-rich prompts for Large Language Models (LLMs).

## What is This?

PromptCraft helps engineers move from simple "prompting" to detailed "specifying." Instead of writing a single paragraph, you fill out distinct sections (like Task, Context, Schemas, and Examples) through an interactive CLI. The tool then assembles these inputs into a perfectly formatted prompt, ensuring better and more accurate code generation from LLMs.

## Key Features

- **Interactive Prompt Builder**: A guided, menu-driven interface to build prompts piece by piece.
- **Configuration Management**: Initialize a project with its specific tech stack (`.promptcraft.yml`).
- **Stateful Sessions**: Save, list, and load complex prompt specifications.
- **Direct LLM Execution**: Run your generated prompts directly against the OpenAI API and get formatted, syntax-highlighted output in your terminal.
- **Clipboard Support**: Quickly copy a generated prompt to your clipboard.

## Installation

This project is managed with Poetry.

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd promptcraft-cli
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```

3.  **Set your OpenAI API Key:**
    The `run` command requires access to the OpenAI API. Set your key as an environment variable.
    ```bash
    export OPENAI_API_KEY='your-secret-api-key'
    ```
    *Tip: Add this line to your shell's configuration file (`.zshrc`, `.bashrc`) to make it permanent.*

## Quickstart Guide

1.  **Initialize a Project:**
    Navigate to your project's directory and run `init`. This will create a `.promptcraft.yml` file to store your project's context.
    ```bash
    poetry run promptcraft init
    ```

2.  **Create a Prompt:**
    Run the main interactive command to start building your prompt.
    ```bash
    poetry run promptcraft
    ```
    Use the menu to define the persona, task, context, and more.

3.  **Save and Generate:**
    - Use the **"💾 Save Session As..."** option in the menu to save your work.
    - Use the **"✨ Generate and Copy Prompt ✨"** option to copy the final prompt to your clipboard.

4.  **List Saved Sessions:**
    See all your saved prompt sessions.
    ```bash
    poetry run promptcraft list
    ```

5.  **Run a Prompt:**
    Execute a saved prompt directly against the LLM.
    ```bash
    poetry run promptcraft run <your-session-name>
    ```
    The response will be streamed to your terminal with syntax highlighting.
