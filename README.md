# Tableau de bord de mes chaînes YouTube

Chaque matin, GitHub Actions récupère les stats publiques (abonnés, vues, nombre de vidéos),
les ajoute à `data/history.json` et republie la page `index.html`.

## Mise en place (une seule fois)

1. **Clé API** : console.cloud.google.com → nouveau projet → activer *YouTube Data API v3* → Identifiants → Créer une clé API.
2. **Dépôt GitHub** : crée un dépôt, pousse-y tout ce dossier (y compris `.github/`).
3. **Secret** : Settings → Secrets and variables → Actions → New repository secret → nom `YOUTUBE_API_KEY`, valeur = ta clé.
4. **Chaînes** : édite `channels.json` avec tes `@handles` ou identifiants `UC…`.
5. **Pages** : Settings → Pages → Source : *GitHub Actions*.
6. **Premier lancement** : onglet Actions → *Mise à jour des stats YouTube* → Run workflow.

L'adresse du tableau de bord s'affiche à la fin du workflow (et dans Settings → Pages).

## Bon à savoir

- L'heure du cron est en UTC : `0 8` = 9h à Paris l'hiver, 10h l'été (passe à `0 7` en été).
  GitHub peut décaler l'exécution de quelques minutes.
- L'historique commence le jour du premier lancement : les courbes se remplissent jour après jour.
- L'API publique ne donne pas le temps de visionnage, les impressions ni le CTR : il faudrait l'API YouTube Analytics (OAuth) pour ça.
- Le dépôt étant public, l'historique l'est aussi (ce sont des chiffres déjà publics sur YouTube).
