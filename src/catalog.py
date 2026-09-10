from dataclasses import dataclass


@dataclass(frozen=True)
class Assessment:
    """Uma rubrica de quatro fatores, 0-25 cada, mais a prosa que os sustenta.

    O total é derivado e nunca armazenado: se um fator muda, o total muda
    junto, e as duas coisas não têm como divergir.
    """

    scores: tuple[int, int, int, int]
    note: str

    def __post_init__(self) -> None:
        if len(self.scores) != 4:
            raise ValueError(f"a rubrica tem quatro fatores, recebi {len(self.scores)}")
        for i, score in enumerate(self.scores):
            if not 0 <= score <= 25:
                raise ValueError(f"fator {i} fora da faixa 0-25: {score}")
        # Nota vazia é número sem justificativa — exatamente o que este desenho impede.
        if not self.note.strip():
            raise ValueError("uma avaliação sem nota é um número sem justificativa")

    @property
    def total(self) -> int:
        return sum(self.scores)


# Faixas de `formality`, do mais aderente à forma original ao mais livre. Nenhuma é
# demérito: dizem para que a versão serve, não o quanto ela vale.
_METHOD_BANDS: tuple[tuple[int, str], ...] = (
    (75, "formal"),       # preserva sintaxe e léxico do original; serve exegese
    (55, "balanced"),     # preserva a forma onde ela comunica, reescreve onde atrapalha
    (35, "functional"),   # traduz a intenção da sentença, reestruturando a sintaxe
    (0, "paraphrase"),    # reescreve em idioma contemporâneo, com liberdade do parafraseador
)


@dataclass(frozen=True)
class CatalogEntry:
    """Metadados editoriais de uma versão.

    Três naturezas de campo convivem aqui, e só duas delas moram neste arquivo:

    * **descritivos** (`text_base`, `formality`) — fato verificável sobre a obra;
    * **editoriais** (`trust`, `respect`) — julgamento com rubrica escrita;
    * **calculados** (integridade, legibilidade) — derivados do texto canônico, que
      moram em ``data/stats/metrics.json`` e nunca aqui: um campo calculado escrito
      à mão apodrece em silêncio na primeira correção de versículo.

    Rubrica de `trust` — confiança de que o texto português deriva dos originais
    hebraico e grego, e não de uma tradução intermediária ou de base indeterminada.
    É proveniência filológica, separada da aceitação social e do método. Os quatro
    fatores, em ordem fixa (a ordem é o contrato, a tupla não é nomeada):

    1. **Origem direta** — traduzida do hebraico e do grego, não a partir de uma
       tradução em língua moderna.
    2. **Base manuscrita** — amplitude e antiguidade dos manuscritos. Texto crítico
       acima de Textus Receptus, Textus Receptus acima de base não declarada.
    3. **Comissão** — corpo tradutor identificável e com credencial acadêmica.
    4. **Transparência** — método e texto-base publicamente documentados pela editora.

    Rubrica de `respect` — aceitação no meio evangélico e acadêmico brasileiro. Não
    mede qualidade de tradução: `trust` trata disso, e os dois divergem de propósito.

    1. **Púlpito** — uso corrente em pregação e liturgia no Brasil.
    2. **Seminário** — adoção como texto de referência no ensino teológico.
    3. **Literatura** — frequência de citação em obra teológica publicada em português.
    4. **Transversalidade** — aceitação fora de um único campo eclesiástico. Uma versão
       respeitadíssima dentro de um campo e rejeitada fora dele pontua na média, não
       no pico.
    """

    code: str
    name: str
    year: int | None
    publisher: str | None
    license: str  # "public-domain" | "copyright"
    scope: str    # "full" | "nt"
    # Edição do Novo Testamento grego por trás da tradução: "textus-receptus" |
    # "critical" | "eclectic" | None (base não declarada e não inferível com
    # segurança). Só o NT: o Antigo de praticamente toda versão em circulação parte
    # do Texto Massorético, então o campo não distinguiria nada ali. Nenhuma versão
    # do acervo usa Texto Majoritário — que não é o mesmo que Textus Receptus — e
    # por isso ele não está no vocabulário. Registra qual base foi usada, jamais qual
    # base é melhor.
    text_base: str | None
    # 0-100 no eixo entre seguir a estrutura do original (100) e seguir a fluência do
    # português (0). `method` é a faixa em que este número cai, e é derivado dele.
    formality: int
    trust: Assessment
    respect: Assessment

    @property
    def method(self) -> str:
        return next(name for floor, name in _METHOD_BANDS if self.formality >= floor)


_ENTRIES: tuple[CatalogEntry, ...] = (
    CatalogEntry(
        "ACF", "Almeida Corrigida e Fiel", 1994, "SBTB", "copyright", "full",
        "textus-receptus", 92,
        Assessment(
            (22, 15, 20, 18),
            "Revisão da Almeida cotejada com o Textus Receptus por comissão da SBTB, que "
            "declara a base textual sem ambiguidade — daí a transparência alta. A base "
            "manuscrita é o que segura a nota: o Textus Receptus repousa sobre poucos "
            "manuscritos e todos tardios, e a revisão trabalha sobre texto português "
            "preexistente tanto quanto sobre o grego.",
        ),
        Assessment(
            (24, 14, 17, 15),
            "Circulação de púlpito muito alta, sustentada por um campo eclesiástico coeso "
            "que a adota como texto único. É essa mesma exclusividade que segura os outros "
            "três fatores: fora do campo Textus Receptus ela é pouco adotada em seminário, "
            "pouco citada e frequentemente contestada, e o discurso de fidelidade exclusiva "
            "que a acompanha aprofunda a divisão em vez de atenuá-la.",
        ),
    ),
    CatalogEntry(
        "ARA", "Almeida Revista e Atualizada", 1993, "SBB", "copyright", "full",
        "critical", 88,
        Assessment(
            (25, 24, 24, 20),
            "Traduzida do hebraico e do grego por comissão da Sociedade Bíblica do Brasil, "
            "sobre texto crítico, com método declarado em prefácio. Perde pontos só na "
            "transparência, porque a documentação da base textual usada em cada decisão "
            "nunca foi publicada em aparato.",
        ),
        Assessment(
            (25, 24, 24, 22),
            "É o texto padrão do púlpito brasileiro há três gerações, e a citação-padrão da "
            "literatura teológica em português. Adotada em seminário de praticamente todas "
            "as tradições, o que sustenta a transversalidade; ela não chega ao teto apenas "
            "porque o campo Textus Receptus a rejeita por princípio.",
        ),
    ),
    CatalogEntry(
        "ARC", "Almeida Revista e Corrigida", 1995, "SBB", "copyright", "full",
        "textus-receptus", 90,
        Assessment(
            (25, 17, 22, 18),
            "Linhagem Almeida trabalhada direto sobre hebraico e grego por comissão da SBB, "
            "o que mantém origem e comissão altas. A base do Novo Testamento permanece na "
            "tradição do Textus Receptus, mais estreita e mais tardia que a crítica, e a "
            "editora não publicou aparato das decisões de revisão.",
        ),
        Assessment(
            (24, 19, 20, 19),
            "Uso litúrgico amplo e antigo, principalmente em tradições que preferem a dicção "
            "clássica de Almeida. Em seminário e em citação foi em boa medida substituída "
            "pela ARA, e a base Textus Receptus limita sua aceitação no ensino acadêmico "
            "sem, porém, torná-la contestada como a ACF.",
        ),
    ),
    CatalogEntry(
        "AS21", "Almeida Século 21", 2009, "Vida Nova", "copyright", "full",
        "critical", 85,
        Assessment(
            (25, 24, 21, 18),
            "Revisão feita a partir dos originais sobre texto crítico, por equipe "
            "identificada e ligada a instituições de ensino. A comissão é menor e menos "
            "documentada academicamente que as da SBB, e a editora publicou pouco sobre os "
            "critérios adotados em cada decisão textual.",
        ),
        Assessment(
            (15, 21, 21, 21),
            "Boa reputação técnica no ensino e citação regular em literatura publicada, "
            "puxadas pela própria Vida Nova. A circulação de púlpito nunca decolou frente à "
            "ARA e à NVI, e é isso que segura a nota: o problema é alcance, não recepção — "
            "onde é conhecida, é aceita transversalmente.",
        ),
    ),
    CatalogEntry(
        "JFAA", "Almeida Atualizada", None, None, "copyright", "full",
        None, 85,
        Assessment(
            (15, 12, 10, 8),
            "Edição da linhagem Almeida cuja procedência não se conseguiu determinar: não há "
            "editora atribuível, comissão identificada nem declaração de texto-base. Os três "
            "fatores baixos registram falta de informação verificável, não defeito constatado "
            "no texto; a origem fica na média porque a linhagem Almeida parte comprovadamente "
            "dos originais, mas não se sabe o que esta edição em particular revisou.",
        ),
        Assessment(
            (10, 8, 9, 8),
            "Circula quase só como arquivo digital, sem edição impressa de referência. "
            "Praticamente não aparece em seminário nem em citação acadêmica, e a procedência "
            "indeterminada é o que impede sua adoção mesmo por quem usa a linhagem Almeida.",
        ),
    ),
    CatalogEntry(
        "KJA", "King James Atualizada", 1999, "Abba Press", "copyright", "full",
        "eclectic", 62,
        Assessment(
            (18, 17, 15, 15),
            "Trabalha sobre os originais, mas com a King James inglesa como referência "
            "declarada de estilo e de escolha lexical, o que insere uma camada entre o "
            "leitor e o grego. A base textual é mista e não se alinha de forma consistente "
            "nem ao Textus Receptus nem ao texto crítico, e a comissão é pouco documentada.",
        ),
        Assessment(
            (14, 11, 12, 13),
            "Uso de púlpito restrito e adoção acadêmica pequena. A marca King James no "
            "título atrai um público e afasta outro, e a base eclética a deixa sem apoio "
            "firme nem no campo Textus Receptus nem no campo do texto crítico.",
        ),
    ),
    CatalogEntry(
        "KJF", "King James Fiel", 1611, "BVBooks", "copyright", "full",
        "textus-receptus", 95,
        Assessment(
            (5, 15, 16, 14),
            "Vertida da King James inglesa de 1611, não do grego, o que praticamente zera o "
            "fator de origem direta independentemente do rigor literal do resultado. A base "
            "é Textus Receptus, declarada com clareza, e a editora documenta a opção, então "
            "transparência e base manuscrita seguram a nota acima do piso.",
        ),
        Assessment(
            (15, 9, 10, 11),
            "Adotada por um público específico que valoriza a linhagem King James, com "
            "presença de púlpito perceptível nesse recorte. Fora dele é quase ausente do "
            "ensino e da citação, justamente por ser tradução de tradução.",
        ),
    ),
    CatalogEntry(
        "NAA", "Nova Almeida Atualizada", 2017, "SBB", "copyright", "full",
        "critical", 82,
        Assessment(
            (25, 25, 25, 20),
            "Revisão da ARA conduzida pela SBB direto sobre hebraico e grego, sobre a edição "
            "crítica mais recente disponível e por comissão de especialistas nomeados. Só a "
            "transparência fica abaixo do teto: os princípios de revisão foram publicados, "
            "mas não o aparato das decisões individuais.",
        ),
        Assessment(
            (23, 24, 23, 23),
            "Adoção rápida em seminário e em publicação desde 2017, herdando a posição da "
            "ARA. No púlpito a substituição ainda está em curso, já que muita congregação "
            "segue lendo a ARA; a aceitação transversal é das mais altas do acervo.",
        ),
    ),
    CatalogEntry(
        "NBV", "Nova Bíblia Viva", 2007, "Mundo Cristão", "copyright", "full",
        "critical", 38,
        Assessment(
            (12, 17, 14, 12),
            "Revisão da Bíblia Viva, que descende da Living Bible inglesa, com cotejo "
            "posterior contra os originais — a origem fica na média por essa dupla camada, "
            "não por erro no texto. A comissão de revisão e os critérios de cotejo são pouco "
            "documentados publicamente.",
        ),
        Assessment(
            (14, 10, 11, 13),
            "Usada sobretudo em leitura devocional e trabalho com público novo, com pouca "
            "presença de púlpito formal. Não é adotada como texto de referência em "
            "seminário, e quase não é citada em literatura teológica.",
        ),
    ),
    CatalogEntry(
        "NTLH", "Nova Tradução na Linguagem de Hoje", 1988, "SBB", "copyright", "full",
        "critical", 40,
        Assessment(
            (25, 23, 22, 12),
            "Tradução nova a partir do hebraico e do grego, por comissão da SBB, sobre texto "
            "crítico. A transparência é o fator fraco: o princípio de equivalência dinâmica "
            "é declarado, mas as decisões de reformulação não são rastreáveis a partir da "
            "edição publicada.",
        ),
        Assessment(
            (18, 18, 19, 20),
            "Amplamente aceita para leitura pública, catequese e trabalho com público novo, e "
            "reconhecida nesse papel em quase todas as tradições — daí a transversalidade "
            "ser o fator mais alto. Não é usada como texto de exposição nem de argumento "
            "doutrinário, o que limita púlpito, seminário e citação.",
        ),
    ),
    CatalogEntry(
        "NVI", "Nova Versão Internacional", None, "Biblica", "copyright", "full",
        "critical", 65,
        Assessment(
            (25, 24, 23, 18),
            "A edição portuguesa foi traduzida dos originais por comissão brasileira, "
            "seguindo os princípios editoriais da NVI internacional, sobre texto crítico. "
            "Perde na transparência porque a edição de referência não é determinável a "
            "partir do que a editora publica.",
        ),
        Assessment(
            (24, 21, 22, 21),
            "Circulação de púlpito enorme desde os anos 2000, sobretudo em igrejas "
            "evangélicas de linha mais recente, e citação frequente em literatura popular e "
            "acadêmica. Em seminário divide espaço com ARA e NAA, e parte do meio "
            "confessional mais tradicional a vê como excessivamente livre.",
        ),
    ),
    CatalogEntry(
        "NVT", "Nova Versão Transformadora", 2016, "Mundo Cristão", "copyright", "full",
        "critical", 48,
        Assessment(
            (25, 24, 22, 14),
            "Tradução dos originais sobre texto crítico, por equipe brasileira seguindo o "
            "método da New Living Translation. A comissão é identificada mas de credencial "
            "acadêmica menos verificável que as da SBB, e a documentação editorial das "
            "escolhas de tradução é escassa.",
        ),
        Assessment(
            (18, 17, 18, 19),
            "Recepção boa e crescente desde 2016 em pregação expositiva e literatura "
            "devocional. Ainda é recente demais para figurar como texto de referência em "
            "seminário, e sua aceitação é mais firme nas mesmas tradições que já adotam a NVI.",
        ),
    ),
    CatalogEntry(
        "TB", "Tradução Brasileira", 2010, "SBB", "public-domain", "full",
        "critical", 93,
        Assessment(
            (25, 22, 23, 20),
            "Traduzida dos originais por comissão luso-brasileira com participação de "
            "hebraístas e helenistas de peso, e o Novo Testamento partiu de Westcott-Hort, "
            "que é reconstrução crítica — antiga, porém, o que segura o fator de base "
            "manuscrita frente às edições Nestle-Aland atuais.",
        ),
        Assessment(
            (15, 23, 24, 23),
            "Prestígio acadêmico duradouro: é citada como referência de literalidade e "
            "estudada em seminário, e o domínio público facilitou sua circulação em obra "
            "publicada. O uso de púlpito é baixo, porque a dicção de 1917 pesa na leitura "
            "em voz alta.",
        ),
    ),
    CatalogEntry(
        "BLIVRE", "Bíblia Livre", 2018, None, "public-domain", "full",
        None, 80,
        Assessment(
            (20, 10, 13, 12),
            "Projeto colaborativo aberto, sem comissão identificável e sem declaração de "
            "texto-base, o que penaliza dois fatores por falta de informação verificável e "
            "não por erro constatado no texto. Onde foi possível conferir, o trabalho parte "
            "dos originais, e é isso que sustenta o fator de origem direta.",
        ),
        Assessment(
            (10, 11, 12, 12),
            "Circula quase exclusivamente por ser de domínio público, o que a leva a "
            "aplicativos e projetos de software mais do que a púlpitos. Ausência de comissão "
            "reconhecível é o que a mantém fora do ensino e da citação acadêmica.",
        ),
    ),
    CatalogEntry(
        "ALM1911", "Almeida 1911", 1911, None, "public-domain", "full",
        "textus-receptus", 90,
        Assessment(
            (25, 15, 18, 12),
            "Linhagem Almeida trabalhada sobre os originais, o que mantém a origem no teto. "
            "O Novo Testamento segue a tradição do Textus Receptus, e a edição de 1911 não "
            "traz comissão nomeada nem documentação editorial que se possa consultar hoje.",
        ),
        Assessment(
            (10, 17, 18, 15),
            "Hoje é sobretudo objeto de estudo histórico da linhagem Almeida e fonte de "
            "citação em obras sobre a história da tradução em português. Praticamente não é "
            "lida em púlpito, e o português de 1911 restringe seu uso corrente.",
        ),
    ),
    CatalogEntry(
        "OL", "O Livro", 2000, "Biblica", "copyright", "full",
        "critical", 25,
        Assessment(
            (10, 15, 13, 12),
            "Paráfrase em português europeu construída na tradição da Living Bible, com "
            "cotejo contra os originais mas sem partir deles — daí a origem baixa. A equipe "
            "não é publicamente identificada e a editora documenta pouco o método.",
        ),
        Assessment(
            (14, 11, 12, 13),
            "Uso devocional e de leitura corrida, com alguma presença em púlpito como texto "
            "de apoio. Não é adotada em seminário nem citada em argumento doutrinário, o que "
            "é esperado de uma paráfrase e não um defeito dela.",
        ),
    ),
    CatalogEntry(
        "MENS", "A Mensagem", 2016, "Editora Vida", "copyright", "full",
        "critical", 15,
        Assessment(
            (5, 15, 12, 8),
            "Recebe nota baixa não por ser paráfrase, mas porque é uma paráfrase inglesa — a "
            "The Message, de Eugene Peterson — vertida para o português, com duas camadas "
            "entre o leitor e o grego. O original inglês parte do texto crítico, o que "
            "sustenta a base manuscrita; a equipe de versão para o português e seus critérios "
            "quase não são documentados.",
        ),
        Assessment(
            (10, 9, 11, 10),
            "Lida como literatura devocional e citada como tal, raramente como texto de "
            "leitura pública. Em seminário aparece como objeto de comentário sobre "
            "tradução, não como referência, e parte do meio evangélico brasileiro a rejeita "
            "pela liberdade do parafraseador.",
        ),
    ),
    CatalogEntry(
        "VFL", "Versão Fácil de Ler", 2017, "Bible League International", "copyright", "full",
        "critical", 42,
        Assessment(
            (24, 22, 17, 12),
            "Traduzida dos originais sobre texto crítico por equipe da Bible League, com "
            "vocabulário deliberadamente restrito para leitor iniciante. A comissão é pouco "
            "documentada e a editora publica pouco sobre a base textual concreta, o que "
            "penaliza os dois últimos fatores por falta de informação verificável.",
        ),
        Assessment(
            (12, 13, 14, 16),
            "Distribuída sobretudo em trabalho missionário e de alfabetização bíblica, com "
            "pouca presença em púlpito e em seminário. É bem recebida no papel a que se "
            "propõe em tradições diferentes, e é isso que deixa a transversalidade acima dos "
            "outros fatores.",
        ),
    ),
)

CATALOG: dict[str, CatalogEntry] = {e.code: e for e in _ENTRIES}


def get(code: str) -> CatalogEntry:
    return CATALOG[code]


def paraphrase_codes() -> frozenset[str]:
    """As versões cuja faixa de método é paráfrase. A comparação de comprimento entre
    versões é inválida para elas, e o catálogo é onde isso está declarado."""
    return frozenset(e.code for e in _ENTRIES if e.method == "paraphrase")
