%% This script currently only works from the linux box due to hardcoded paths 

%function convertTrust_BIDS(sublist(s))
%% set up dirs
% Get script directory using mfilename instead of desktop editor
scriptname = mfilename('fullpath');
[codedir,~,~] = fileparts(scriptname);
% Eliminate cd
cd(codedir);
addpath(codedir)
cd ..
maindir = '/ZPOOL/data/projects/g25';%pwd;

% Partner is Neutral Keep=4, Neutral Share=3, Far=2, Close=1
% Reciprocate is Yes=1, No=0
% cLeft is the left option
% cRight is the right option
% high/low value option will randomly flip between left/right
% 
% sublist(s) = sublist(s)ect number
%/data/projects/g25/stimuli/Scan-Investment_Game/logs
rawdata='/ZPOOL/data/projects/gambling-2025/stimuli/Scan-Investment_Game/logs';

% sublist = [10322, 10042, 10062, 10221, 10252, 10366, 10562, 10665, 11033, 11039, 11115, 10687, 10005, 10191, 10106, 10033, 10150, 10364, 10231, 10358, 10255, 10283, 10029, 10123, 10352, 10080];
sublist = [11039];

for s = 1:length(sublist)

try
    
    for r = 1:3
        %r=1;
        fname = fullfile(rawdata,num2str(sublist(s)),sprintf('sub-%03d_task-trust_run-%d_raw.csv',sublist(s),r));
        if exist(fname,'file')
            disp("First checkpoint");
            fid = fopen(fname,'r');
        else
            fprintf('sub-%d -- Investment Game, Run %d: No data found.\n', sublist(s), r)
            continue;
        end
        
        % Read the data using readtable
        T = readtable(fname, 'Delimiter', ',');
        fclose(fid);

        % Extract the columns you need using the new column names
        outcomeonset = T.outcome_onset; % locked to the presentation of outcome
        choiceonset = T.onset; % locked to the presentation of decision screen
        RT = T.rt;
        Partner = T.Partner;
        reciprocate = T.Reciprocate;
        response = T.highlow; % high/low choice
        trust_val = T.resp; % investment amount (0-8, with NaN or specific value for no response)
        cLeft = T.cLeft;
        cRight = T.cRight;
        options = [cLeft, cRight];
        bpress = T.bpress; % button press response
        duration_trial = T.duration; % trial duration

        
        fname = sprintf('sub-%03d_task-trust_run-%01d_events.tsv',sublist(s),r);
        output = fullfile(maindir,'bids',['sub-' num2str(sublist(s))],'func');
        disp(output);
        if ~exist(output,'dir')
            disp("Second checkpoint");
            mkdir(output)
        end
        fid = fopen(fullfile(output,fname),'w');
        fprintf(fid,'onset\tduration\ttrial_type\tresponse_time\ttrust_value\tchoice\tcLow\tcHigh\n');
        
        for t = 1:length(choiceonset)
            
            % Check for missing responses (adjust this condition based on your no-response coding)
            is_missed = isnan(trust_val(t)) || trust_val(t) == 999 || isnan(bpress(t));
            
            % Determine trial type based on Partner value
            if (Partner(t) == 1)
                trial_type = 'close_good';
            elseif (Partner(t) == 2)
                trial_type = 'close_bad';
            elseif (Partner(t) == 3)
                trial_type = 'far_good';
            elseif (Partner(t) == 4)
                trial_type = 'far_bad';
            end
            
            % Handle string/cell array for response
            if iscell(response)
                resp_str = response{t};
            else
                if strcmpi(response(t), 'high') || response(t) == 1
                    resp_str = 'high';
                else
                    resp_str = 'low';
                end
            end
            
            % "String values containing tabs MUST be escaped using double quotes.
            % Missing and non applicable values MUST be coded as "n/a"."
            % http://bids.neuroimaging.io/bids_spec.pdf
            
            if is_missed
                % Missed trial
                fprintf(fid,'%f\t%f\t%s\t%f\t%s\t%s\t%d\t%d\n',...
                    choiceonset(t), 3, 'missed_trial', ...
                    3, 'n/a', 'n/a', ...
                    min(options(t,:)), max(options(t,:)));
            else
                if trust_val(t) == 0
                    % No trust (kept all money)
                    fprintf(fid,'%f\t%f\t%s\t%f\t%d\t%s\t%d\t%d\n',...
                        choiceonset(t), RT(t), ['choice_' trial_type], ...
                        RT(t), 0, resp_str, ...
                        min(options(t,:)), max(options(t,:)));
                else
                    % Trusted some amount
                    fprintf(fid,'%f\t%f\t%s\t%f\t%d\t%s\t%d\t%d\n',...
                        choiceonset(t), RT(t), ['choice_' trial_type], ...
                        RT(t), trust_val(t), resp_str, ...
                        min(options(t,:)), max(options(t,:)));
                    
                    % Add outcome event
                    if reciprocate(t) == 1
                        fprintf(fid,'%f\t%f\t%s\t%f\t%d\t%s\t%d\t%d\n',...
                            outcomeonset(t), 2, ['outcome_' trial_type '_recip'], ...
                            RT(t), trust_val(t), resp_str, ...
                            min(options(t,:)), max(options(t,:)));
                    else
                        fprintf(fid,'%f\t%f\t%s\t%f\t%d\t%s\t%d\t%d\n',...
                            outcomeonset(t), 2, ['outcome_' trial_type '_defect'], ...
                            RT(t), trust_val(t), resp_str, ...
                            min(options(t,:)), max(options(t,:)));
                    end
                end
            end
            
        end
        fclose(fid);
    end
    catch ME
    disp(ME.message)
    msg = sprintf('sub-%d: check line %d', sublist(s), ME.stack(1).line);
    disp(msg);
    continue  % Move to next subject instead of stopping
end
end
