# Markdown diagram test

This ordinary Markdown document contains two sequence diagrams.

## Mermaid

```mermaid
sequenceDiagram
    participant Alice
    participant Bob
    Alice->>Bob: Hello!
    Bob-->>Alice: Hi, Alice!
```

## PlantUML

```plantuml
@startuml
participant Alice
participant Bob
Alice -> Bob: Hello!
Bob --> Alice: Hi, Alice!
@enduml
```

## Try editing

Run `:MdRender toggle` to switch between this source and its rendered view.
Run `:vertical MdRender split` to edit beside a live preview.
