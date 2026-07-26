import { Bot, LoaderCircle, Mic, MicOff, Volume2 } from "lucide-react";
import {
  PropsWithChildren,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";

import { ironHouseChatApi } from "../api/