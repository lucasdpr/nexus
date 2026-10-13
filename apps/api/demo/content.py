"""Documentos fictícios da NovaForja Industrial para a demonstração e para a avaliação do RAG.

Todo o conteúdo é inventado. Os fatos (prazos, valores, limites) são consultados por
`questions.json`: mudar um número aqui exige mudar a pergunta correspondente lá.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoDocument:
    filename: str
    title: str
    collection: str
    # Uma string por página (PDF) ou por bloco de parágrafos (DOCX).
    pages: tuple[str, ...]


MANUAL_CX200 = DemoDocument(
    filename="manual-compressor-cx-200.pdf",
    title="Manual do Compressor CX-200",
    collection="Engenharia de Manutenção",
    pages=(
        """MANUAL DO COMPRESSOR CX-200 - REVISÃO 4
NovaForja Industrial - Engenharia de Manutenção

1. Apresentação
O compressor de parafuso CX-200 fornece ar comprimido para as linhas de estampagem e de
pintura da planta de Betim. Este manual descreve operação, manutenção e garantia.

2. Especificações técnicas
Pressão máxima de trabalho: 10 bar.
Vazão nominal: 32 m³/min a 8 bar.
Potência do motor: 200 kW (tensão de 440 V trifásica).
Temperatura máxima de descarga do ar: 105 °C.
Nível de ruído: 78 dB(A) a um metro, com a carenagem fechada.
Capacidade do reservatório de óleo: 45 litros.""",
        """3. Operação
A partida é feita pelo painel frontal, com o registro de saída fechado. Aguarde a pressão
de óleo estabilizar em 3 bar antes de abrir o registro. A parada normal exige o ciclo de
alívio de pressão: o compressor trabalha em vazio por 30 segundos antes de desligar.

3.1 Parada de emergência
O botão de emergência corta a alimentação do motor imediatamente. Depois do acionamento,
não religue o equipamento antes de a Engenharia de Manutenção inspecionar o motivo da
parada. A temperatura de descarga acima de 110 °C desarma o compressor automaticamente.""",
        """4. Manutenção preventiva
Os intervalos abaixo valem para operação em ambiente com poeira normal.
Troca do filtro de ar: a cada 2.000 horas de operação.
Troca do filtro de óleo: a cada 4.000 horas de operação.
Troca do óleo sintético: a cada 8.000 horas, ou uma vez por ano, o que vier primeiro.
Troca do elemento separador de óleo: a cada 6.000 horas.
Inspeção das correias e acoplamentos: a cada 1.000 horas.
Calibração da válvula de segurança: uma vez por ano, por laboratório credenciado.
Todo serviço deve ser registrado na ficha de manutenção do equipamento.""",
        """5. Garantia
O prazo de garantia é de 24 meses a partir da data de instalação, limitado a 12.000 horas
de operação. A garantia depende do cumprimento das manutenções preventivas do capítulo 4,
registradas na ficha de manutenção. A garantia não cobre desgaste natural de filtros e
correias, nem danos causados por óleo diferente do especificado.

6. Falhas comuns
Temperatura alta de descarga: verifique o nível de óleo e a limpeza do radiador.
Pressão que não sobe: verifique vazamentos e o estado da válvula de admissão.
Consumo de óleo elevado: substitua o elemento separador de óleo.
Contato do suporte técnico do fabricante: 0800 555 0123, em dias úteis das 8h às 18h.""",
    ),
)

PLANO_LINHA2 = DemoDocument(
    filename="plano-manutencao-preventiva-linha-2.docx",
    title="Plano de Manutenção Preventiva - Linha 2",
    collection="Engenharia de Manutenção",
    pages=(
        """PLANO DE MANUTENÇÃO PREVENTIVA - LINHA 2 DE ESTAMPAGEM
Responsável: Marina Duarte, gerente de Engenharia de Manutenção.

Objetivo
Garantir a disponibilidade da Linha 2 acima de 94% ao mês, com paradas programadas aos
domingos, das 6h às 14h. As paradas fora desse horário só ocorrem por falha ou emergência.

Prensa hidráulica PH-02
Verificação do nível e da temperatura do óleo hidráulico: diária, no início do turno.
Troca do óleo hidráulico: a cada 6 meses.
Inspeção das mangueiras de alta pressão: mensal. Mangueiras com mais de 5 anos são trocadas.

Ponte rolante PR-04
Inspeção dos cabos de aço: semanal. A troca é obrigatória se houver mais de 6 fios rompidos
em um passo do cabo. Teste de carga com 125% da capacidade nominal: a cada 12 meses.

Indicadores
A meta de tempo médio de reparo (MTTR) é de 3 horas. O tempo médio entre falhas (MTBF)
deve ficar acima de 400 horas. Os indicadores são revisados na reunião mensal de manutenção.""",
    ),
)

PROCEDIMENTO_LOTO = DemoDocument(
    filename="procedimento-bloqueio-etiquetagem-loto.pdf",
    title="Procedimento de Bloqueio e Etiquetagem (LOTO)",
    collection="Segurança do Trabalho",
    pages=(
        """PROCEDIMENTO DE BLOQUEIO E ETIQUETAGEM (LOTO) - PS-014
NovaForja Industrial - Segurança do Trabalho

1. Finalidade
Impedir a energização ou a liberação de energia acidental durante manutenção e limpeza de
máquinas, em conformidade com a NR-10 e a NR-12.

2. Quem pode aplicar o bloqueio
Somente trabalhadores com treinamento LOTO válido. O treinamento é renovado a cada 24 meses
e sempre que houver mudança de equipamento ou de procedimento. Cada trabalhador usa o seu
próprio cadeado vermelho, com o nome e a matrícula na etiqueta.""",
        """3. Etapas do bloqueio
1) Avisar a operação e o supervisor da área sobre a parada.
2) Desligar o equipamento pelo comando normal.
3) Abrir a chave geral e todos os dispositivos de isolamento de energia.
4) Aplicar o cadeado pessoal e a etiqueta de bloqueio em cada ponto de isolamento.
5) Liberar ou drenar as energias residuais: pressão hidráulica, ar comprimido, molas e
   capacitores. Capacitores devem esperar 5 minutos para descarregar.
6) Testar a ausência de tensão com instrumento adequado e tentar a partida para confirmar o
   bloqueio. Só depois o serviço pode começar.""",
        """4. Retirada do bloqueio
Cada trabalhador retira apenas o seu próprio cadeado, ao fim do serviço, depois de conferir
que ferramentas e pessoas estão fora da máquina. Se o trabalhador não estiver na planta, o
cadeado só pode ser retirado pelo supervisor, com autorização da Segurança do Trabalho e
após tentar contato com o trabalhador. Esse caso gera registro formal.

5. Registros
Todo bloqueio é registrado no formulário FS-014, guardado por 5 anos.
Acidentes e quase acidentes relacionados ao LOTO são comunicados à CIPA em até 24 horas.""",
    ),
)

POLITICA_EPI = DemoDocument(
    filename="politica-epi.pdf",
    title="Política de Equipamentos de Proteção Individual",
    collection="Segurança do Trabalho",
    pages=(
        """POLÍTICA DE EQUIPAMENTOS DE PROTEÇÃO INDIVIDUAL (EPI) - PO-007
NovaForja Industrial - Segurança do Trabalho

1. Fornecimento
A empresa fornece os EPIs gratuitamente, com Certificado de Aprovação (CA) válido. A entrega
é registrada em ficha individual, assinada pelo trabalhador.

2. Uso obrigatório por área
Estampagem: protetor auricular (atenuação mínima de 20 dB), óculos de segurança e luvas de
raspa. Pintura: respirador com filtro para vapores orgânicos e macacão. Solda: máscara de
solda, avental de raspa e luvas de cano longo.""",
        """3. Substituição
Os EPIs são substituídos quando danificados ou vencidos. O protetor auricular de espuma é
descartável e trocado a cada turno. O respirador tem os filtros trocados a cada 30 dias, ou
antes disso se o trabalhador sentir odor ou dificuldade para respirar. Capacetes têm validade
de 5 anos a partir da fabricação.

4. Responsabilidades e penalidades
O trabalhador deve usar, guardar e conservar o EPI e comunicar qualquer dano. A recusa em
usar o EPI obrigatório configura ato faltoso, com advertência na primeira ocorrência.""",
    ),
)

CONTRATO_ACOS = DemoDocument(
    filename="contrato-fornecimento-acos-vale-forte.pdf",
    title="Contrato de Fornecimento - Aços Vale Forte",
    collection="Suprimentos",
    pages=(
        """CONTRATO DE FORNECIMENTO Nº 2025/118
Contratante: NovaForja Industrial Ltda.   Contratada: Aços Vale Forte S.A.

Cláusula 1 - Objeto
Fornecimento de chapas de aço carbono laminadas a frio, espessuras de 0,8 mm a 3,0 mm,
conforme especificação técnica do Anexo I, para uso nas linhas de estampagem.

Cláusula 2 - Vigência
O contrato vigora por 36 meses, a partir de 1º de março de 2025, podendo ser prorrogado por
igual período mediante aditivo escrito.""",
        """Cláusula 3 - Preço e reajuste
O preço base é de R$ 6.480,00 por tonelada, posto na planta de Betim. O preço é reajustado a
cada 12 meses pela variação do IPCA, limitada a 8% ao ano.

Cláusula 4 - Prazos de entrega
Cada pedido de compra é atendido em até 15 dias corridos. O pedido mínimo é de 20 toneladas.
O atraso na entrega sujeita a Contratada a multa de 0,5% por dia sobre o valor da parcela
em atraso, limitada a 10% do valor da parcela.""",
        """Cláusula 5 - Qualidade
Os lotes são aceitos mediante certificado de qualidade. Lotes com mais de 2% de peças fora
da tolerância dimensional podem ser rejeitados, e a Contratada repõe o material sem custo
em até 10 dias corridos.

Cláusula 6 - Pagamento
O pagamento ocorre em 45 dias após o recebimento da nota fiscal.

Cláusula 7 - Rescisão
Qualquer das partes pode rescindir o contrato com aviso prévio de 90 dias, sem multa. A
rescisão imediata é permitida em caso de descumprimento grave não corrigido em 15 dias.""",
    ),
)

POLITICA_COMPRAS = DemoDocument(
    filename="politica-de-compras.docx",
    title="Política de Compras",
    collection="Suprimentos",
    pages=(
        """POLÍTICA DE COMPRAS - PO-021
NovaForja Industrial - Suprimentos

Alçadas de aprovação
Compras de até R$ 5.000,00 são aprovadas pelo gestor da área solicitante.
Compras acima de R$ 5.000,00 e até R$ 50.000,00 exigem a aprovação do gerente de Suprimentos.
Compras acima de R$ 50.000,00 exigem a aprovação da diretoria.

Cotações
Compras acima de R$ 5.000,00 exigem no mínimo 3 cotações. A escolha de um fornecedor que não
apresentou o menor preço deve ser justificada por escrito. Compras emergenciais podem ter
uma única cotação, com justificativa registrada em até 2 dias úteis.

Homologação de fornecedores
Todo novo fornecedor passa por homologação, que inclui consulta de regularidade fiscal,
avaliação de qualidade e verificação de práticas de segurança do trabalho. A homologação
vale por 24 meses.""",
    ),
)

PARECER_REAJUSTE = DemoDocument(
    filename="parecer-clausula-reajuste.pdf",
    title="Parecer Jurídico - Cláusula de Reajuste",
    collection="Jurídico e Contratos",
    pages=(
        """PARECER JURÍDICO Nº 031/2025 - CLÁUSULA DE REAJUSTE
Assunto: contrato de fornecimento nº 2025/118 (Aços Vale Forte S.A.)

1. Consulta
A Diretoria de Suprimentos perguntou se o teto de 8% ao ano na cláusula de reajuste é
oponível à Contratada caso o IPCA ultrapasse esse patamar.

2. Análise
O teto é válido e oponível, pois foi livremente pactuado entre partes empresariais. Se o IPCA
acumulado em 12 meses for superior a 8%, o reajuste aplicado será de 8%, sem direito a
compensação posterior da diferença, salvo previsão expressa em aditivo.""",
        """3. Recomendações
Recomenda-se registrar a data-base do reajuste (1º de março) no sistema de contratos para
evitar reajuste fora do período. A prorrogação da vigência por mais 36 meses exige aditivo
escrito assinado antes do término do prazo original.

4. Conclusão
Não há óbice jurídico à aplicação do teto. O parecer vale apenas para o contrato citado e
não se estende a outros fornecedores.""",
    ),
)

DOCUMENTS: tuple[DemoDocument, ...] = (
    MANUAL_CX200,
    PLANO_LINHA2,
    PROCEDIMENTO_LOTO,
    POLITICA_EPI,
    CONTRATO_ACOS,
    POLITICA_COMPRAS,
    PARECER_REAJUSTE,
)
