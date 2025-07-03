**PROJETO FINAL DE RSA - Sistema de Notificações de Acidentes Rodoviários**

A crescente adoção de tecnologias de comunicação veicular tem impulsionado o desenvolvimento de soluções inteligentes para a segurança rodoviária, gestão de tráfego e eficiência dos transportes. Neste contexto, existe um padrão europeu designado ITS-G5 onde se destacam dois tipos fundamentais de mensagens:

- **CAMs (Cooperative Awareness Messages)** – enviadas periodicamente por veículos para informar sobre a sua posição, direção, velocidade, entre outros parâmetros essenciais para a perceção situacional da rede.
- **DENMs (Decentralized Environmental Notification Messages)** – utilizadas para notificar eventos perigosos, como acidentes, condições perigosas da via ou obstáculos na estrada.

Este projeto insere-se nesse cenário, cujo propósito é simular um sistema de alerta de acidentes entre veículos com base na troca de mensagens CAM e DENM. A simulação é realizada com o auxílio da plataforma VANETZA, que implementa o protocolo ITS-G5 sobre MQTT, e permite uma interação realista entre OBUs (On-Board Units). Adicionalmente, foi criada uma interface visual com Leaflet e GPX para representar rotas reais e o comportamento dos veículos durante a simulação.

Através desta estrutura, é possível simular cenários de acidente onde: um veículo emite uma mensagem DENM ao detetar um acidente, os veículos próximos reagem, desviando-se automaticamente da rota original, e onde uma ambulância é acionada e enviada automaticamente para o local do acidente.
