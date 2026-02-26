"""DoLT CLI — Typer 앱 정의."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from dolt import __version__
from dolt.models.config import ChunkMode, DoltConfig, EmbeddingProvider, ExportTarget
from dolt.utils.logging import setup_logging

app = typer.Typer(
    name="dolt",
    help="DoLT — Document-native ELT Engine",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"DoLT v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    config: str | None = typer.Option(None, "--config", "-c", help="설정 파일 경로"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="상세 로그 출력"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="에러만 출력"),
    log_level: str = typer.Option("INFO", "--log-level", help="DEBUG/INFO/WARNING/ERROR"),
    version: bool | None = typer.Option(
        None, "--version", callback=_version_callback, is_eager=True
    ),
) -> None:
    """DoLT — Document-native ELT Engine."""
    level = "ERROR" if quiet else ("DEBUG" if verbose else log_level)
    setup_logging(level)

    app.info.context_settings = {"obj": {"config_path": config}}


# ── dolt ingest ───────────────────────────────────────────

@app.command()
def ingest(
    source: str = typer.Argument(..., help="파일 경로, 디렉토리, 또는 URL"),
    recursive: bool = typer.Option(True, "--recursive", "-r", help="하위 디렉토리 포함"),
    pattern: str = typer.Option("*", "--pattern", "-p", help="파일 glob 패턴"),
    force: bool = typer.Option(False, "--force", "-f", help="unchanged 파일도 재수집"),
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """파일, 디렉토리, 또는 URL에서 문서를 수집합니다."""
    cfg = DoltConfig.load(config)
    from dolt.ingestion.ingestor import Ingestor
    from dolt.storage.local_store import LocalStore

    store = LocalStore(cfg.storage.path)
    ingestor = Ingestor(store)

    try:
        docs = ingestor.ingest(source, recursive=recursive, pattern=pattern)
    except Exception as e:
        console.print(f"[red]오류:[/red] {e}")
        raise typer.Exit(1)

    table = Table(title="수집 결과")
    table.add_column("상태", style="bold")
    table.add_column("수")
    new = sum(1 for d in docs if d.status.value == "new")
    updated = sum(1 for d in docs if d.status.value == "updated")
    unchanged = sum(1 for d in docs if d.status.value == "unchanged")
    table.add_row("new", str(new))
    table.add_row("updated", str(updated))
    table.add_row("unchanged", str(unchanged))
    console.print(table)


# ── dolt parse ────────────────────────────────────────────

@app.command()
def parse(
    doc_id: str | None = typer.Option(None, "--doc-id", help="특정 문서만 파싱"),
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """수집된 문서를 파싱합니다."""
    cfg = DoltConfig.load(config)
    from dolt.ingestion.ingestor import Ingestor
    from dolt.parsing.registry import create_default_registry
    from dolt.storage.local_store import LocalStore

    store = LocalStore(cfg.storage.path)
    registry = create_default_registry()
    ingestor = Ingestor(store)
    docs = store.load_documents()

    if doc_id:
        docs = [d for d in docs if d.doc_id == doc_id]

    parsed = 0
    for doc in docs:
        try:
            parser = registry.get_parser(doc.file_ext)
            file_path = str(ingestor.get_file_path(doc))
            structured = parser.parse(file_path, doc.doc_id)
            store.save_parsed(structured)
            parsed += 1
            n_sec = len(structured.sections)
            console.print(
                f"  [green]✓[/green] {doc.file_name}"
                f" ({structured.total_pages}p, {n_sec} sections)"
            )
        except Exception as e:
            console.print(f"  [red]✗[/red] {doc.file_name}: {e}")

    console.print(f"\n파싱 완료: {parsed}/{len(docs)}")


# ── dolt chunk ────────────────────────────────────────────

@app.command()
def chunk(
    mode: ChunkMode = typer.Option(ChunkMode.HYBRID, "--mode", "-m", help="token/structure/hybrid"),
    max_tokens: int = typer.Option(512, "--max-tokens", help="청크 최대 토큰 수"),
    overlap: int = typer.Option(50, "--overlap", help="오버랩 토큰 수"),
    doc_id: str | None = typer.Option(None, "--doc-id"),
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """파싱된 문서를 청크로 분할합니다."""
    cfg = DoltConfig.load(config, cli_overrides={
        "chunking": {"mode": mode.value, "max_tokens": max_tokens, "overlap_tokens": overlap}
    })
    from dolt.metadata.enricher import MetadataEnricher
    from dolt.pipeline.orchestrator import _create_chunker
    from dolt.storage.local_store import LocalStore

    store = LocalStore(cfg.storage.path)
    chunker = _create_chunker(cfg)
    enricher = MetadataEnricher()
    docs = store.load_documents()

    if doc_id:
        docs = [d for d in docs if d.doc_id == doc_id]

    total_chunks = 0
    for doc in docs:
        parsed = store.load_parsed(doc.doc_id)
        if not parsed:
            console.print(
                f"  [yellow]⚠[/yellow] {doc.file_name}:"
                " 파싱 데이터 없음 (dolt parse 먼저 실행)"
            )
            continue

        chunks = chunker.chunk(parsed)
        chunks = enricher.enrich(chunks, parsed)
        store.save_chunks(doc.doc_id, chunks)
        total_chunks += len(chunks)
        console.print(f"  [green]✓[/green] {doc.file_name}: {len(chunks)} chunks")

    console.print(f"\n청킹 완료: {total_chunks} chunks")


# ── dolt embed ────────────────────────────────────────────

@app.command()
def embed(
    provider: EmbeddingProvider = typer.Option(
        EmbeddingProvider.OPENAI, "--provider", help="openai/cohere/local"
    ),
    model: str | None = typer.Option(None, "--model", help="임베딩 모델"),
    batch_size: int = typer.Option(100, "--batch-size"),
    doc_id: str | None = typer.Option(None, "--doc-id"),
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """청크를 벡터로 임베딩합니다."""
    overrides: dict = {"embedding": {"provider": provider.value, "batch_size": batch_size}}
    if model:
        overrides["embedding"]["model"] = model
    cfg = DoltConfig.load(config, cli_overrides=overrides)

    from dolt.models.chunk import EmbeddedChunk
    from dolt.pipeline.orchestrator import _create_embedding_provider
    from dolt.storage.local_store import LocalStore

    store = LocalStore(cfg.storage.path)
    try:
        emb_provider = _create_embedding_provider(cfg)
    except Exception as e:
        console.print(f"[red]오류:[/red] {e}")
        raise typer.Exit(1)

    docs = store.load_documents()
    if doc_id:
        docs = [d for d in docs if d.doc_id == doc_id]

    total = 0
    for doc in docs:
        chunks = store.load_chunks(doc.doc_id)
        if not chunks:
            continue

        texts = [c.content for c in chunks]
        try:
            vectors = emb_provider.embed(texts)
        except Exception as e:
            console.print(f"  [red]✗[/red] {doc.file_name}: {e}")
            continue

        embedded = [
            EmbeddedChunk(
                chunk_id=c.chunk_id, doc_id=c.doc_id, content=c.content,
                chunk_type=c.chunk_type, chunk_index=c.chunk_index,
                token_count=c.token_count, vector=v,
                embedding_model=emb_provider.model_name(),
                embedding_dim=emb_provider.dimension(),
                metadata=c.metadata,
            )
            for c, v in zip(chunks, vectors)
        ]
        store.save_embeddings(doc.doc_id, embedded)
        total += len(embedded)
        console.print(f"  [green]✓[/green] {doc.file_name}: {len(embedded)} embedded")

    console.print(f"\n임베딩 완료: {total} chunks")


# ── dolt export ───────────────────────────────────────────

@app.command(name="export")
def export_cmd(
    target: ExportTarget = typer.Option(
        ExportTarget.JSON, "--target", help="qdrant/pinecone/weaviate/json/postgres"
    ),
    collection: str = typer.Option("dolt_documents", "--collection"),
    output: str = typer.Option(".dolt/export.json", "--output", help="JSON export 경로"),
    doc_id: str | None = typer.Option(None, "--doc-id"),
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """임베딩된 청크를 내보냅니다."""
    overrides: dict = {"export": {"target": target.value}}
    if target == ExportTarget.QDRANT:
        overrides["export"]["qdrant"] = {"collection": collection}
    elif target == ExportTarget.WEAVIATE:
        overrides["export"]["weaviate"] = {"collection": collection}
    elif target == ExportTarget.JSON:
        overrides["export"]["json"] = {"output": output}
    cfg = DoltConfig.load(config, cli_overrides=overrides)

    from dolt.pipeline.orchestrator import _create_exporter
    from dolt.storage.local_store import LocalStore

    store = LocalStore(cfg.storage.path)
    exporter = _create_exporter(cfg)

    docs = store.load_documents()
    if doc_id:
        docs = [d for d in docs if d.doc_id == doc_id]

    all_chunks = []
    for doc in docs:
        chunks = store.load_embeddings(doc.doc_id)
        all_chunks.extend(chunks)

    if not all_chunks:
        console.print("[yellow]내보낼 임베딩 데이터가 없습니다.[/yellow]")
        raise typer.Exit(1)

    try:
        result = exporter.export(all_chunks)
    except Exception as e:
        console.print(f"[red]오류:[/red] {e}")
        raise typer.Exit(1)

    console.print(
        f"\n[green]Export 완료:[/green]"
        f" {result.success}/{result.total} → {result.destination}"
    )


# ── dolt run ──────────────────────────────────────────────

@app.command()
def run(
    source: str = typer.Argument(..., help="파일 경로, 디렉토리, 또는 URL"),
    mode: ChunkMode = typer.Option(ChunkMode.HYBRID, "--mode", "-m"),
    max_tokens: int = typer.Option(512, "--max-tokens"),
    overlap: int = typer.Option(50, "--overlap"),
    provider: EmbeddingProvider = typer.Option(EmbeddingProvider.OPENAI, "--provider"),
    model: str | None = typer.Option(None, "--model"),
    target: ExportTarget = typer.Option(ExportTarget.JSON, "--target"),
    collection: str = typer.Option("dolt_documents", "--collection"),
    output: str = typer.Option(".dolt/export.json", "--output"),
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """전체 파이프라인을 한 번에 실행합니다."""
    overrides: dict = {
        "chunking": {"mode": mode.value, "max_tokens": max_tokens, "overlap_tokens": overlap},
        "embedding": {"provider": provider.value},
        "export": {"target": target.value},
    }
    if model:
        overrides["embedding"]["model"] = model
    if target == ExportTarget.QDRANT:
        overrides["export"]["qdrant"] = {"collection": collection}
    elif target == ExportTarget.JSON:
        overrides["export"]["json"] = {"output": output}

    cfg = DoltConfig.load(config, cli_overrides=overrides)

    from dolt.pipeline.orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(cfg)

    with console.status("[bold green]파이프라인 실행 중..."):
        result = orchestrator.run(source)

    # 결과 출력
    table = Table(title="파이프라인 결과")
    table.add_column("단계", style="bold")
    table.add_column("건수", justify="right")
    table.add_column("소요시간", justify="right")
    table.add_column("상태")

    for stage_name in ["ingest", "parse", "chunk", "enrich", "embed", "export"]:
        stage = result.stages.get(stage_name)
        if stage:
            if stage.status == "success":
                status_style = "green"
            elif stage.status == "partial":
                status_style = "yellow"
            else:
                status_style = "red"
            table.add_row(
                stage_name,
                str(stage.count),
                f"{stage.elapsed_seconds:.1f}s",
                f"[{status_style}]{stage.status}[/{status_style}]",
            )

    console.print(table)
    console.print(f"\n총 소요시간: {result.elapsed_seconds:.1f}s")


# ── dolt status ───────────────────────────────────────────

@app.command()
def status(
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """로컬 저장소 상태를 확인합니다."""
    cfg = DoltConfig.load(config)
    from dolt.storage.local_store import LocalStore

    store = LocalStore(cfg.storage.path)
    docs = store.load_documents()

    new = sum(1 for d in docs if d.status.value == "new")
    updated = sum(1 for d in docs if d.status.value == "updated")
    unchanged = sum(1 for d in docs if d.status.value == "unchanged")

    parsed = sum(1 for d in docs if store.load_parsed(d.doc_id) is not None)
    chunked = sum(len(store.load_chunks(d.doc_id)) for d in docs)
    embedded = sum(len(store.load_embeddings(d.doc_id)) for d in docs)

    console.print("\n[bold]DoLT Status:[/bold]")
    console.print(f"  Documents: {len(docs)} ({new} new, {updated} updated, {unchanged} unchanged)")
    console.print(f"  Parsed:    {parsed}")
    console.print(f"  Chunks:    {chunked}")
    console.print(f"  Embedded:  {embedded}")
    console.print()


# ── dolt clean ────────────────────────────────────────────

@app.command()
def clean(
    all_data: bool = typer.Option(False, "--all", help="전체 .dolt/ 초기화"),
    doc_id: str | None = typer.Option(None, "--doc-id", help="특정 문서 데이터 삭제"),
    config: str | None = typer.Option(None, "--config", "-c"),
) -> None:
    """로컬 저장소 데이터를 삭제합니다."""
    import shutil
    from pathlib import Path

    cfg = DoltConfig.load(config)
    base = Path(cfg.storage.path)

    if all_data:
        if base.exists():
            shutil.rmtree(base)
            console.print("[green]전체 데이터 삭제 완료[/green]")
        else:
            console.print("[yellow].dolt/ 디렉토리가 없습니다[/yellow]")
        return

    if doc_id:
        from dolt.storage.local_store import LocalStore
        store = LocalStore(cfg.storage.path)

        for sub in ["parsed", "chunks", "embeddings"]:
            path = base / sub / f"{doc_id}.json"
            if path.exists():
                path.unlink()

        docs = store.load_documents()
        docs = [d for d in docs if d.doc_id != doc_id]
        store.save_documents(docs)
        console.print(f"[green]문서 {doc_id} 데이터 삭제 완료[/green]")
        return

    console.print("[yellow]--all 또는 --doc-id 옵션을 지정해주세요[/yellow]")
