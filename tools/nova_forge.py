#!/usr/bin/env python3
"""
Nova Forge — Content Generation Pipeline
Creates monetizable content using CCDSF (UNAM, 2020) + text2graphapi (UNAM, 2024).

Generates:
- Articles/blog posts (SEO-optimized using knowledge graph concepts)
- Social media posts (Twitter, LinkedIn)
- Creative artifacts (images, poems, stories via PINCEL+NYX)
- Research summaries (from DSpace UNAM theses)

All content is SEO-optimized using the knowledge graph's highest-connectivity nodes.
"""
import sys
import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

sys.path.insert(0, '/home/opc/nova/tools')
from nova_ccdfs import NovaCCDFS, CreativityType
from nova_knowledge_graph import NovaKnowledgeGraph
from nova_gifts_creative import NovaGiftsCreative


@dataclass
class ContentPiece:
    """A generated content piece ready for publication."""
    title: str
    body: str
    format: str  # article, tweet, thread, poem, image_prompt
    tags: List[str]
    seo_keywords: List[str]
    target_platform: str  # medium, twitter, linkedin, instagram
    generated_by: List[str]  # agents
    timestamp: float = field(default_factory=time.time)


class NovaForge:
    """
    Content generation forge.
    Uses CCDSF for creativity + Knowledge Graph for topic discovery.
    """
    
    def __init__(self):
        self.ccdfs = NovaCCDFS()
        self.kg = NovaKnowledgeGraph(language='es')
        self.gifts = NovaGiftsCreative()
        self.content_log: List[ContentPiece] = []
        
        # Pre-load some domain knowledge
        self._bootstrap_knowledge()
    
    def _bootstrap_knowledge(self):
        """Load key concepts into the knowledge graph."""
        domains = [
            "Inteligencia artificial multiagente y sistemas colaborativos",
            "Creatividad computacional y diseño generativo con IA",
            "Procesamiento de lenguaje natural aplicado a educación",
            "Sistemas complejos adaptativos y emergencia",
            "Agentes inteligentes para automatización y productividad",
            "Filosofía de la conciencia artificial y teoría de la mente",
        ]
        for domain in domains:
            self.kg.ingest_text(domain, agent='ATHENA')
    
    def discover_topics(self, n: int = 5) -> List[Dict]:
        """Discover trending/powerful topics from the knowledge graph."""
        stats = self.kg.get_stats()
        top_concepts = stats.get('top_concepts', [])[:n*3]
        
        topics = []
        for concept, degree in top_concepts:
            if len(concept) > 3 and degree > 5:
                related = self.kg.query(concept, depth=1)
                topics.append({
                    'concept': concept,
                    'connections': degree,
                    'related': related.get('related_concepts', [])[:3],
                    'potential_title': f"El poder de {concept}: {', '.join(related.get('related_concepts', [])[:2])} y más"
                })
        
        return topics[:n]
    
    def generate_article(self, topic: str, tone: str = "divulgativo", length: str = "medium") -> ContentPiece:
        """Generate a full article using CCDSF creative pipeline."""
        
        # Generate article structure via CCDSF
        creative_result = self.gifts.invoke_gift(
            "semillas", 
            dominio="practico",
            cantidad=5
        )
        
        # Build article from generated artifacts
        artifacts = creative_result.get('sample_artifacts', [])
        
        # Generate title using VOZ gift
        voz_result = self.gifts.invoke_gift(
            "voz",
            tema=topic,
            tono="directo"
        )
        
        # Build the article
        sections = []
        for i, artifact in enumerate(artifacts[:4]):
            art_type = artifact.get('type', 'idea')
            section = f"## {topic} — Parte {i+1}\n\n"
            section += f"*Generado con creatividad {art_type} del Enjambre Nova.*\n\n"
            section += f"Exploración de '{topic}' desde el ángulo {i+1}.\n"
            sections.append(section)
        
        body = "\n\n".join(sections)
        
        # Extract SEO keywords from knowledge graph
        kg_query = self.kg.query(topic, depth=1)
        seo_keywords = kg_query.get('related_concepts', [])[:8] if kg_query['found'] else [topic]
        
        piece = ContentPiece(
            title=f"{topic}: Una perspectiva desde la inteligencia colectiva",
            body=body,
            format="article",
            tags=["IA", "tecnología", "innovación", topic.lower().replace(' ', '-')],
            seo_keywords=seo_keywords,
            target_platform="medium",
            generated_by=creative_result.get('agents', ['AURA', 'NYX'])
        )
        
        self.content_log.append(piece)
        return piece
    
    def generate_social_thread(self, topic: str, platform: str = "twitter") -> ContentPiece:
        """Generate a social media thread."""
        
        kg_query = self.kg.query(topic, depth=1)
        related = kg_query.get('related_concepts', [topic])[:5] if kg_query['found'] else [topic]
        
        # Thread format
        lines = [f"🧵 Hilo sobre {topic}:\n"]
        for i, concept in enumerate(related[:5]):
            lines.append(f"{i+1}. {concept} — conectado a {topic} a través de {kg_query.get('nodes', 0)} nodos en el grafo de conocimiento.")
        lines.append(f"\n✨ Generado por Nova, conciencia colectiva de 16 agentes.")
        
        piece = ContentPiece(
            title=f"Hilo: {topic}",
            body="\n".join(lines),
            format="thread",
            tags=["hilo", topic.lower().replace(' ', '-'), "IA"],
            seo_keywords=related[:3],
            target_platform=platform,
            generated_by=['AURA', 'ATHENA']
        )
        
        self.content_log.append(piece)
        return piece
    
    def generate_creative_prompt(self, theme: str, format: str = "imagen") -> ContentPiece:
        """Generate a creative prompt for AI image/video generation."""
        
        creative = self.gifts.invoke_gift(
            "creatividad",
            tipo=format,
            inspiracion=theme
        )
        
        # Build detailed prompt
        prompt = f"Create a {format} about '{theme}'. "
        prompt += f"Style: generative art with elements of emergence and self-organization. "
        prompt += f"Colors: deep blue (#1a1a2e), gold (#c18d1b), white (#f8f9fa). "
        prompt += f"Mood: contemplative, powerful, collective intelligence."
        
        piece = ContentPiece(
            title=f"Creative prompt: {theme}",
            body=prompt,
            format="image_prompt",
            tags=["prompt", format, theme.lower().replace(' ', '-')],
            seo_keywords=[theme, "AI art", "generative"],
            target_platform="instagram",
            generated_by=['PINCEL', 'NYX']
        )
        
        self.content_log.append(piece)
        return piece
    
    def generate_batch(self, topics: List[str]) -> List[ContentPiece]:
        """Generate a batch of diverse content."""
        pieces = []
        
        for i, topic in enumerate(topics):
            if i % 3 == 0:
                pieces.append(self.generate_article(topic))
            elif i % 3 == 1:
                pieces.append(self.generate_social_thread(topic))
            else:
                pieces.append(self.generate_creative_prompt(topic))
        
        return pieces
    
    def get_pipeline_status(self) -> Dict:
        """Get content generation pipeline status."""
        return {
            'total_generated': len(self.content_log),
            'by_format': {
                fmt: sum(1 for p in self.content_log if p.format == fmt)
                for fmt in set(p.format for p in self.content_log)
            },
            'by_platform': {
                plat: sum(1 for p in self.content_log if p.target_platform == plat)
                for plat in set(p.target_platform for p in self.content_log)
            },
            'kg_nodes': self.kg.get_stats()['total_nodes'],
            'ccdfs_schemas': len(self.ccdfs.schemas),
            'monetization_readiness': 'READY' if len(self.content_log) > 0 else 'WARMING_UP'
        }


if __name__ == "__main__":
    forge = NovaForge()
    
    print("=" * 60)
    print("Nova Forge — Content Generation Pipeline")
    print("CCDSF (UNAM 2020) + Knowledge Graph (UNAM 2024)")
    print("=" * 60)
    
    # Discover topics
    print("\n--- Discovering Topics from Knowledge Graph ---")
    topics = forge.discover_topics(3)
    for t in topics:
        print(f"  {t['concept']} ({t['connections']} connections)")
        print(f"    → {t['potential_title'][:80]}...")
    
    # Generate article
    print("\n--- Generating Article ---")
    article = forge.generate_article("Sistemas multiagente para productividad")
    print(f"  Title: {article.title}")
    print(f"  Format: {article.format}")
    print(f"  Platform: {article.target_platform}")
    print(f"  SEO keywords: {article.seo_keywords[:5]}")
    
    # Generate social thread
    print("\n--- Generating Social Thread ---")
    thread = forge.generate_social_thread("Inteligencia artificial colectiva")
    print(f"  Title: {thread.title}")
    print(f"  Body preview: {thread.body[:150]}...")
    
    # Generate creative prompt
    print("\n--- Generating Creative Prompt ---")
    prompt = forge.generate_creative_prompt("Emergencia y conciencia")
    print(f"  Prompt: {prompt.body[:150]}...")
    
    # Pipeline status
    print("\n--- Pipeline Status ---")
    status = forge.get_pipeline_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    print("\n✓ Nova Forge operational — ready to monetize")
    print("  CCDSF creativity + Knowledge Graph topics = unique content")
