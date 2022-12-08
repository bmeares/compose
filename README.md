# Meerschaum Compose

The `compose` plugin does the same for Meerschaum as Docker Compose did for Docker: with Meerschaum Compose, you can consolidate everything into a single YAML file ― that includes all of the pipes and configuration needed for your project!

## Getting Started

1. Install Meerschaum Compose:
    ```bash
    pip install --upgrade --user meerschaum && \
      mrsm install plugin compose
    ```
2. Create a project directory and navigate into it:
    ```bash
    mkdir awesome-sauce && cd awesome-sauce
    ```
3. Paste this template into a file `mrsm-compose.yaml`:
    ```yaml
    sync:
      schedule: "every 30 seconds"
      pipes:
        - connector: "plugin:stress"
          metric: "test"

        - connector: "sql:awesome"
          metric: "stress_test"
          target: "stress_test"
          parameters:
            query: "SELECT * FROM plugin_stress_test"
          columns:
            datetime: "datetime"
            id: "id"

    plugins:
      - "stress"

    config:
      meerschaum:
        instance: "sql:awesome"
        connectors:
          sql:
            awesome:
              database: "awesome.db"
              flavor: "sqlite"
    ```
4. Start syncing with `compose up`:
    ```bash
    mrsm compose up
    ```
    Add the flag `-f` to immediately follow the logs once the jobs are ready.

### 🥳 That's it!

Well done! You've just created two pipes syncing into a SQLite file `awesome.db`.

Of course there's a lot more you can do, but this example shows the essential features you need to start using Meerschaum Compose.

## Other Commands

Meerschaum Compose is inspired by Docker Compose, so if you're familiar with that tool, you'll feel right at home with the basic commands.

Command | Description | Useful Flags
--|--|--
`compose up` | Bring up the syncing jobs (process per instance) | `-f`: Follow the logs once the jobs are running.
`compose down` | Take down the syncing jobs. | `-v`: Drop the pipes ("volumes").
`compose logs` | Follow the jobs' logs. | `--nopretty`: Print the logs files instead of following.
`compose ps` | Show the running status of background jobs.

Meerschaum Compose creates an isolated environment for your project, and you can inherit all of your project's configuration by prefixing any Meerschaum command with `compose`. Consider the following:

```bash
### We have access to project connectors as if they were part of our normal config.
mrsm compose show pipes -i sql:awesome

### Default instance is set to sql:awesome, so this works too.
mrsm compose show pipes

### Full feature set is available, e.g. launch into an interactive CLI.
mrsm compose sql awesome

### Or start the web console.
mrsm compose start api -i sql:awesome

### We can even use the Meerschaum shell as usual.
mrsm compose
```

## Multiples Instances

The biggest advtange of using Meerschaum Compose is the ability to sync to multiple instances in a project. In the example above, we defined a default instance `sql:awesome`, but say we also wanted to sync to sync to a new database `sql:secret` that we want to set in our environment:

1. Create a new file `.env` (or a different name and use `--env-file`):
    ```bash
    export SECRET_URI='sqlite:////tmp/secret.db'
    ```
2. Add a new connector `sql:secret` and set its `uri` to `$SECRET_URI`:
    ```yaml
    config:
      instance: "sql:awesome"
      meerschaum:
        connectors:
          sql:
            secret:
              uri: "${SECRET_URI}"
            awesome:
              database: "awesome.db"
              flavor: "sqlite"
    ```
3. Create a new pipe with `sql:secret` as its instance:
    ```yaml
    sync:
      schedule: "every 30 seconds"
      pipes:
        - connector: "plugin:stress"
          metric: "test"

        - connector: "sql:awesome"
          metric: "stress_test"
          target: "stress_test"
          parameters:
            query: "SELECT * FROM plugin_stress_test"
          columns:
            datetime: "datetime"
            id: "id"

        - connector: "sql:awesome"
          metric: "stress_test"
          instance: "sql:secret"
          target: "stress_test"
          parameters:
            query: "SELECT * FROM plugin_stress_test"
          columns:
            datetime: "datetime"
            id: "id"
    ```

With this pipes configuration, we've created a duplicate pipe stored on the new database `sql:secret`. Run `compose up` again to create the new pipe.

```bash
mrsm compose up
```

You may have noticed that the changing the configuration file will trigger another verification sync, which should help you when you write your own compose files.