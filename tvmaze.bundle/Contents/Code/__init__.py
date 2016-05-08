#!/usr/bin/python

import os
import re
import datetime
import pytvmaze


SUPPORTED_LANGUAGES = [
    'ab', 'sq', 'ar', 'hy', 'az', 'bg', 'zh', 'cs', 'da', 'nl', 'en', 'et',
    'fi', 'fr', 'ka', 'de', 'ga', 'he', 'hi', 'hr', 'hu', 'is', 'it', 'ja',
    'ko', 'no', 'fa', 'pl', 'pt', 'ro', 'ru', 'sr', 'es', 'sv', 'tl', 'th',
    'tr', 'uk', 'ur', 'cy']

def Start():
    Log.Debug("Starting TVMaze Agent")


class TVMazeAgent(Agent.TV_Shows):
    name = "TV Maze"
    languages = SUPPORTED_LANGUAGES
    primary_provider = True
    fallback_agent = False
    accepts_from = None
    contributes_to = None


    # Search for YYYY-MM-DD formatted date
    def regex_date(self, filename):
        Log.Debug(filename)
        re1=('((?:(?:[1]{1}\\d{1}\\d{1}\\d{1})|(?:[2]{1}\\d{3}))[-:\\/.]'
             '(?:[0]?[1-9]|[1][012])[-:\\/.](?:(?:[0-2]?\\d{1})|(?:[3][01]'
             '{1})))(?![\\d])')
        rg = re.compile(re1,re.IGNORECASE|re.DOTALL)
        m = rg.search(filename)
        if m:
            date = m.group()
            return date

    # Search for S01E01 formatted info
    def regex_sxxexx(self, filename):
        Log.Debug(filename)
        re1='(S)'
        re2='(\\d+)'
        re3='(E)'
        rg = re.compile(re1+re2+re3+re2,re.IGNORECASE|re.DOTALL)
        m = rg.search(filename)
        if m:
            ep_info = m.group()
            return ep_info


    def search(self, results, media, lang, manual):
        Log.Debug("Search with TVMazeAgent: " + media.show)
        Log.Debug('Searching tvmaze...')
        shows = pytvmaze.get_show_list(media.show)
        if shows:
            scores = [show.score for show in shows]
            for show in shows:
                Log.Debug(media.show)
                Log.Debug(show.name + ' ' + str(show.maze_id))
                Log.Debug(media.season)
                Log.Debug(media.episode)

                if show.language:
                    lang_code = Locale.Language.Match(show.language)
                    Log.Debug('{lang} ({code})'.format(lang=show.language,
                                                       code=lang_code))
                else:
                    lang_code = Locale.Language.English

                # Scale scores
                if len(scores) > 1:
                    new_score = ((99 * (show.score - min(scores))) / (max(scores) - min(scores))) + 1
                else:
                    new_score = 100

                results.Append(MetadataSearchResult(
                    id = str(show.maze_id),
                    name = show.name,
                    year = int(show.premiered[:4]) if show.premiered else None,
                    lang = lang_code,
                    score = int(new_score)
                ))
                Log.Debug('Result added...')
                Log.Debug(new_score)


    def update(self, metadata, media, lang, force):
        Log.Debug('Update() called...')

        # Get main show info
        show = pytvmaze.get_show(maze_id=int(metadata.id), embed='episodes')
        if show:
            metadata.title = show.name
            metadata.summary = show.summary

            # Get poster if it exists
            if show.image:
                if show.image.get('medium'):
                    med_url = show.image.get('medium')
                    metadata.posters[med_url] = Proxy.Preview(HTTP.Request(med_url).content)
                if show.image.get('original'):
                    orig_url = show.image.get('original')
                    metadata.posters[orig_url] = Proxy.Media(HTTP.Request(orig_url).content)

        # Get Season posters they exist
        Log.Debug('SEASONS: ' + str(media.seasons.keys()))
        for season_num in media.seasons.keys():
            Log.Debug('SEASON: ' + season_num)
            season = metadata.seasons[season_num]

            if show[int(season_num)].image:
                if show[int(season_num)].image.get('medium'):
                    med_url = show[int(season_num)].image.get('medium')
                    season.posters[med_url] = Proxy.Preview(HTTP.Request(med_url).content)
                if show[int(season_num)].image.get('original'):
                    orig_url = show[int(season_num)].image.get('original')
                    season.posters[orig_url] = Proxy.Media(HTTP.Request(orig_url).content)
            elif show.image:
                if show.image.get('medium'):
                    med_url = show.image.get('medium')
                    season.posters[med_url] = Proxy.Preview(HTTP.Request(med_url).content)
                if show.image.get('original'):
                    orig_url = show.image.get('original')
                    season.posters[orig_url] = Proxy.Media(HTTP.Request(orig_url).content)

            # Get data for each episode
            for episode_num in media.seasons[season_num].episodes.keys():
                episode = metadata.seasons[season_num].episodes[episode_num]
                episode_media = media.seasons[season_num].episodes[episode_num].items[0]
                filename = os.path.basename(episode_media.parts[0].file)

                # Number based shows (S01E01 style)
                se_ep = self.regex_sxxexx(filename)
                if se_ep:
                    Log.Debug('Number based episode scheme')
                    ep = pytvmaze.episode_by_number(metadata.id,
                                                    season_num,
                                                    episode_num)

                # Date based shows
                date = self.regex_date(filename)
                if not se_ep and date:
                    Log.Debug('Date based episode scheme')
                    ep = pytvmaze.episodes_by_date(metadata.id,
                                                   date)
                    if len(ep) >= 1:
                        ep = ep[0]


                # If episode found on tvmaze...update its metadata
                if ep:
                    episode.title = ep.title
                    episode.summary = ep.summary
                    try:
                        airdate = datetime.datetime.strptime(ep.airdate, '%Y-%m-%d')
                    except TypeError as e:
                        airdate = ep.airdate
                    episode.originally_available_at = airdate
                    episode.duration = ep.runtime
                    episode.season = ep.season_number
